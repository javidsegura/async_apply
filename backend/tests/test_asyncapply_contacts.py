"""find_contact searches in Python, so a named contact must be one it fetched."""

import asyncio
from importlib import import_module
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from services.asyncapply.stages.utils import Contact, SearchQueries, Shortlist
from services.asyncapply.utils.web import SearchResult

# The package re-exports the function under this name, so reach the module itself.
mod = import_module("services.asyncapply.stages.find_contact")


def _hit(url: str) -> SearchResult:
    return SearchResult(title="Someone", url=url, snippet="works there")


def _contact(url: str, name: str = "Ada", fit_score: float = 4.0) -> Contact:
    return Contact(contact_name=name, contact_linkedin=url, message="hello", fit_score=fit_score)


REAL = "https://www.linkedin.com/in/real-person"


def test_an_invented_profile_is_dropped():
    shortlist = Shortlist(contacts=[_contact(REAL), _contact("https://linkedin.com/in/made-up")])
    kept = shortlist.grounded_in({REAL})
    assert [c.contact_linkedin for c in kept.contacts] == [REAL]


def test_dropping_everyone_records_why():
    shortlist = Shortlist(contacts=[_contact("https://linkedin.com/in/made-up")])
    kept = shortlist.grounded_in({REAL})
    assert kept.contacts == []
    assert kept.reason


def test_only_personal_profiles_count(monkeypatch):
    """Job and company URLs are postings and org pages, not people."""

    async def fake_search(query, limit=8):
        return [
            _hit("https://www.linkedin.com/jobs/view/123"),
            _hit("https://www.linkedin.com/company/acme"),
            _hit(REAL),
        ]

    monkeypatch.setattr(mod, "search", fake_search)
    hits = list(_run(mod._profiles(["q"])).values())
    assert [h.url for h in hits] == [REAL]


def test_the_same_person_found_twice_appears_once(monkeypatch):
    async def fake_search(query, limit=8):
        return [_hit(REAL)]

    monkeypatch.setattr(mod, "search", fake_search)
    assert len(_run(mod._profiles(["a", "b", "c"]))) == 1


def test_a_failed_search_does_not_lose_the_others(monkeypatch):
    async def fake_search(query, limit=8):
        if query == "bad":
            raise RuntimeError("rate limited")
        return [_hit(REAL)]

    monkeypatch.setattr(mod, "search", fake_search)
    assert list(_run(mod._profiles(["bad", "good"]))) == [REAL]


def test_the_wider_round_runs_only_when_the_first_finds_nobody(monkeypatch):
    """The fallback is a Python widening, not the model improvising."""
    seen = []

    async def fake_search(query, limit=8):
        seen.append(query)
        return [_hit(REAL)] if "software engineer linkedin" in query else []

    async def fake_fetch(url):
        return "profile text"

    async def fake_ask(stage, system, user, output):
        if output is SearchQueries:
            return SearchQueries(queries=[])
        return Shortlist(contacts=[_contact(REAL)])

    monkeypatch.setattr(mod, "search", fake_search)
    monkeypatch.setattr(mod, "fetch_or_empty", fake_fetch)
    monkeypatch.setattr(mod, "ask", fake_ask)

    ctx = SimpleNamespace(profile={"cv": {"summary": "s", "experience": []}})

    result = _run(mod.find_contact("Acme", "Engineer", ctx))
    assert result.contacts
    assert mod._queries("Acme", "Engineer")[0] in seen
    assert mod._wider_queries("Acme", "Engineer")[0] in seen


def test_nothing_found_returns_an_empty_shortlist(monkeypatch):
    """Query proposals are asked for up front, in parallel with the fixed
    search, so that call does happen even here. What must never happen is
    asking the model to choose a contact when there is nobody to choose from."""

    async def fake_search(query, limit=8):
        return []

    async def fake_ask(stage, system, user, output):
        if output is SearchQueries:
            return SearchQueries(queries=[])
        raise AssertionError("the model must not be asked to choose when nobody was found")

    monkeypatch.setattr(mod, "search", fake_search)
    monkeypatch.setattr(mod, "ask", fake_ask)

    ctx = SimpleNamespace(profile={})

    result = _run(mod.find_contact("Acme", "Engineer", ctx))
    assert result.contacts == []
    assert result.reason


def _run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("field", ["contact_name", "contact_linkedin", "message"])
def test_a_contact_cannot_omit_its_evidence(field):
    """Name, profile and message are required, so a half-filled contact cannot exist."""
    kwargs = {"contact_name": "Ada", "contact_linkedin": REAL, "message": "hi"}
    del kwargs[field]
    with pytest.raises(ValidationError):
        Contact(**kwargs)


def test_location_is_never_part_of_the_search_query():
    """Measured live: appending the posting's location string took a real
    search from 6 hits to 0. Location must stay out of the query entirely."""
    queries = mod._queries("Acme", "Engineer")
    assert not any("Madrid" in q for q in queries)


def test_location_reaches_the_model_as_selection_context(monkeypatch):
    captured = {}

    async def fake_search(query, limit=8):
        return [_hit(REAL)]

    async def fake_fetch(url):
        return "profile text"

    async def fake_ask(stage, system, user, output):
        if output is SearchQueries:
            return SearchQueries(queries=[])
        captured["user_prompt"] = user
        return Shortlist(contacts=[_contact(REAL)])

    monkeypatch.setattr(mod, "search", fake_search)
    monkeypatch.setattr(mod, "fetch_or_empty", fake_fetch)
    monkeypatch.setattr(mod, "ask", fake_ask)

    ctx = SimpleNamespace(profile={"cv": {"summary": "s", "experience": []}})
    _run(mod.find_contact("Acme", "Engineer", ctx, location="Madrid, Spain"))

    assert "Madrid, Spain" in captured["user_prompt"]


def test_llm_proposed_queries_run_alongside_the_fixed_ones(monkeypatch):
    """The model's query proposals add candidates on top of the fixed
    queries; they never replace them."""
    FROM_FIXED = "https://www.linkedin.com/in/from-fixed"
    FROM_LLM = "https://www.linkedin.com/in/from-llm"

    async def fake_search(query, limit=8):
        if query == "Acme's own weird internal title linkedin":
            return [_hit(FROM_LLM)]
        return [_hit(FROM_FIXED)]

    async def fake_fetch(url):
        return "profile text"

    async def fake_ask(stage, system, user, output):
        if output is SearchQueries:
            return SearchQueries(queries=["Acme's own weird internal title linkedin"])
        return Shortlist(
            contacts=[_contact(FROM_FIXED, name="A"), _contact(FROM_LLM, name="B")]
        )

    monkeypatch.setattr(mod, "search", fake_search)
    monkeypatch.setattr(mod, "fetch_or_empty", fake_fetch)
    monkeypatch.setattr(mod, "ask", fake_ask)

    ctx = SimpleNamespace(profile={"cv": {"summary": "s", "experience": []}})
    result = _run(mod.find_contact("Acme", "Engineer", ctx))

    assert {c.contact_linkedin for c in result.contacts} == {FROM_FIXED, FROM_LLM}


def test_a_failed_query_proposal_does_not_break_the_fixed_search(monkeypatch):
    from services.asyncapply.llm import AgentError

    async def fake_search(query, limit=8):
        return [_hit(REAL)]

    async def fake_fetch(url):
        return "profile text"

    async def fake_ask(stage, system, user, output):
        if output is SearchQueries:
            raise AgentError("provider down")
        return Shortlist(contacts=[_contact(REAL)])

    monkeypatch.setattr(mod, "search", fake_search)
    monkeypatch.setattr(mod, "fetch_or_empty", fake_fetch)
    monkeypatch.setattr(mod, "ask", fake_ask)

    ctx = SimpleNamespace(profile={"cv": {"summary": "s", "experience": []}})
    result = _run(mod.find_contact("Acme", "Engineer", ctx))

    assert result.contacts


def test_grounded_in_sorts_by_fit_score_best_first():
    shortlist = Shortlist(
        contacts=[
            _contact(REAL, name="Low", fit_score=2.0),
            _contact("https://linkedin.com/in/high", name="High", fit_score=5.0),
        ]
    )
    kept = shortlist.grounded_in({REAL, "https://linkedin.com/in/high"})
    assert [c.contact_name for c in kept.contacts] == ["High", "Low"]


def test_grounded_in_hard_caps_at_three_even_if_the_model_listed_more():
    urls = [f"https://linkedin.com/in/p{i}" for i in range(5)]
    shortlist = Shortlist(contacts=[_contact(u, name=str(i), fit_score=float(i)) for i, u in enumerate(urls)])
    kept = shortlist.grounded_in(set(urls))
    assert len(kept.contacts) == 3
    assert [c.contact_name for c in kept.contacts] == ["4", "3", "2"]


def test_jd_text_reaches_the_model_for_scoring(monkeypatch):
    captured = {}

    async def fake_search(query, limit=8):
        return [_hit(REAL)]

    async def fake_fetch(url):
        return "profile text"

    async def fake_ask(stage, system, user, output):
        if output is SearchQueries:
            return SearchQueries(queries=[])
        captured["user_prompt"] = user
        return Shortlist(contacts=[_contact(REAL)])

    monkeypatch.setattr(mod, "search", fake_search)
    monkeypatch.setattr(mod, "fetch_or_empty", fake_fetch)
    monkeypatch.setattr(mod, "ask", fake_ask)

    ctx = SimpleNamespace(profile={"cv": {"summary": "s", "experience": []}})
    _run(mod.find_contact("Acme", "Engineer", ctx, jd_text="We need someone who owns Kubernetes at scale."))

    assert "owns Kubernetes at scale" in captured["user_prompt"]
