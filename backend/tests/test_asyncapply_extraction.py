"""Tests for the extract_jd stage: fetching is Python's job, not the model's."""

from importlib import import_module

import pytest

from services.asyncapply.stages import extract_jd
from services.asyncapply.stages.utils import Extraction

extract_module = import_module("services.asyncapply.stages.extract_jd")

PAGE = "x" * 1000


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


pytestmark = pytest.mark.anyio


def _stub(monkeypatch, *, page="", alternatives=None, seen=None):
    """Wire the stage's three collaborators to recorded fakes."""
    pages = dict(alternatives or {})

    async def fetch(url):
        if seen is not None:
            seen.setdefault("fetched", []).append(url)
        return pages.get(url, page)

    async def search(query, limit=8):
        if seen is not None:
            seen["query"] = query
        return [extract_module.search.__globals__["SearchResult"](title="t", url=u, snippet="")
                for u in pages if u != "origin"] if pages else []

    async def ask(stage, system, user, output):
        if seen is not None:
            seen["user"] = user
        return Extraction(extraction_failed=False, jd_text="JD")

    monkeypatch.setattr(extract_module, "fetch_or_empty", fetch)
    monkeypatch.setattr(extract_module, "search", search)
    monkeypatch.setattr(extract_module, "ask", ask)


def test_is_url_only_matches_a_bare_link() -> None:
    assert extract_module.is_url("https://example.com/job") is True
    assert extract_module.is_url("  http://example.com/job  ") is True
    assert extract_module.is_url("We are hiring, see https://x.com") is False
    assert extract_module.is_url("pasted job description text") is False


async def test_a_url_is_fetched_before_the_model_sees_it(monkeypatch) -> None:
    seen: dict = {}
    _stub(monkeypatch, page=PAGE, seen=seen)

    result = await extract_jd("https://example.com/job")

    assert result.jd_text == "JD"
    assert seen["fetched"] == ["https://example.com/job"]
    assert seen["user"] == PAGE


async def test_pasted_text_is_never_fetched(monkeypatch) -> None:
    """Offering a lookup for text we already hold is pure waste."""
    seen: dict = {}
    _stub(monkeypatch, seen=seen)

    pasted = "Senior Engineer at Acme. " * 40
    await extract_jd(pasted)

    assert "fetched" not in seen
    assert seen["user"] == pasted


async def test_an_empty_page_is_a_failure_without_asking_the_model(monkeypatch) -> None:
    async def nothing(url):
        return ""

    async def no_results(query, limit=8):
        return []

    async def boom(*args, **kwargs):
        raise AssertionError("the model must not be asked about a page that never loaded")

    monkeypatch.setattr(extract_module, "fetch_or_empty", nothing)
    monkeypatch.setattr(extract_module, "search", no_results)
    monkeypatch.setattr(extract_module, "ask", boom)

    result = await extract_jd("https://example.com/job")

    assert result.extraction_failed is True
    assert "example.com" in (result.reason or "")


async def test_an_unusable_link_falls_back_to_searching(monkeypatch) -> None:
    """A login wall should send us looking for the posting elsewhere."""
    from services.asyncapply.utils.web import SearchResult

    async def fetch(url):
        return "" if "origin" in url else PAGE

    async def search(query, limit=8):
        assert "senior backend engineer" in query
        return [SearchResult(title="t", url="https://board.example/jd", snippet="")]

    async def ask(stage, system, user, output):
        assert user == PAGE
        return Extraction(extraction_failed=False, jd_text="JD")

    monkeypatch.setattr(extract_module, "fetch_or_empty", fetch)
    monkeypatch.setattr(extract_module, "search", search)
    monkeypatch.setattr(extract_module, "ask", ask)

    result = await extract_jd("https://origin.example/senior-backend-engineer")
    assert result.jd_text == "JD"
