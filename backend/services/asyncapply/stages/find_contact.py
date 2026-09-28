"""Stage 3: shortlist people to reach out to and draft messages. Prompt: modes/find_contact.md."""

import asyncio

from services.asyncapply.context import AsyncApplyContext, load_mode
from services.asyncapply.llm import AgentError, ask
from services.asyncapply.stages.utils import SearchQueries, Shortlist
from services.asyncapply.utils.web import SearchResult, fetch_or_empty, search

# Profiles to read in full and offer the model. Enough to choose between,
# few enough that the browser loads stay quick.
MAX_CANDIDATES = 8

# Below this the first round was too thin to choose from, so the broader
# queries run as well. A quoted long title often matches only one person.
MIN_CANDIDATES = 3

# Only a personal profile is a person: linkedin.com/jobs/ and /company/ URLs
# are postings and org pages.
PROFILE_MARKER = "linkedin.com/in/"


def _queries(company: str, role: str) -> list[str]:
    """The first round of searches: the people most worth reaching.

    Args:
        company: The company name.
        role: The role title.

    Returns:
        Queries in order of preference. Search operators are omitted on
        purpose; the backend is not Google and returns nothing for them.
        Location is deliberately not in here -- measured live, appending the
        posting's own location string ("San Sebastian de los Reyes, Community
        of Madrid, Spain") took Siemens from 6 hits to 0. It is handed to the
        model as selection context in find_contact() instead, so it narrows
        who gets picked, not what the search can find in the first place.
    """
    return [
        f'{company} "{role}" linkedin',
        f'{company} "engineering manager" linkedin',
        f'"technical recruiter" {company} linkedin',
    ]


def _wider_queries(company: str, role: str) -> list[str]:
    """The fallback round, used only when the first found nobody.

    Dropping the quoted title and the seniority wording is what usually
    rescues a company whose titles do not match the posting's phrasing.

    Args:
        company: The company name.
        role: The role title.

    Returns:
        Broader queries.
    """
    return [
        f"{company} software engineer linkedin",
        f"{company} recruiter linkedin",
        f"{company} {role.split(',')[0]} team linkedin",
    ]


async def _llm_queries(company: str, role: str, location: str | None) -> list[str]:
    """Ask the model for extra query phrasings, run the same way as the fixed ones.

    The model never touches a search tool or sees a result -- it only writes
    strings here, which find_contact() then runs exactly like _queries()'s
    fixed ones. Fabrication stays impossible regardless of how creative the
    phrasing gets: the final contact is still checked against real search
    results, not against anything this call claims.

    Args:
        company: The company name.
        role: The role title.
        location: The role's own location, if the posting stated one.

    Returns:
        Up to 5 proposed queries, or an empty list if the call failed -- this
        is an enhancement on top of the proven fixed queries, not something
        the whole stage should fail over.
    """
    user_prompt = f"Company: {company}\nRole: {role}\n" + (f"Role location: {location}\n" if location else "")
    try:
        result = await ask(
            "find_contact", load_mode("find_contact_queries"), user_prompt, SearchQueries
        )
    except AgentError:
        return []
    return result.queries[:5]


async def _profiles(
    queries: list[str], found: dict[str, SearchResult] | None = None
) -> dict[str, SearchResult]:
    """Run searches in parallel and keep the personal profiles they surface.

    Args:
        queries: The searches to run.
        found: Profiles from an earlier round, added to rather than replaced.

    Returns:
        Profiles by URL, in the order the queries surfaced them.
    """
    rounds = await asyncio.gather(*(search(q) for q in queries), return_exceptions=True)

    found = found if found is not None else {}
    for results in rounds:
        if isinstance(results, BaseException):
            continue
        for hit in results:
            if PROFILE_MARKER in hit.url.lower():
                found.setdefault(hit.url, hit)
    return found


def _dossier(hits: list[SearchResult], pages: list[str]) -> str:
    """Format the candidates for the model to choose between.

    Args:
        hits: The profile search hits.
        pages: Each hit's fetched page text, positionally aligned.

    Returns:
        One block per candidate, carrying the URL the model must copy back.
    """
    blocks = []
    for hit, page in zip(hits, pages, strict=True):
        body = page.strip() or hit.snippet
        blocks.append(f"### {hit.title}\nURL: {hit.url}\n\n{body[:4000]}")
    return "\n\n".join(blocks)


# How much of the posting to show when scoring candidates against it. A
# posting rarely needs more than this to convey what the role actually is.
JD_EXCERPT_CHARS = 3000


async def find_contact(
    company: str,
    role: str,
    context: AsyncApplyContext,
    location: str | None = None,
    jd_text: str | None = None,
) -> Shortlist:
    """Shortlist outreach targets at the company and draft a message to each.

    The model never calls a search tool: offered one alongside a schema, it
    answered without searching and invented a contact in 8 of 8 measured
    attempts. So it only ever writes query strings (_llm_queries) or picks
    from a list of profiles this function already fetched -- searching and
    fetching are both done here in Python, and the final choice is checked
    against the real URLs found (Shortlist.grounded_in), so a name cannot
    reach the output without a real profile behind it. The model's proposed
    queries run alongside the fixed ones rather than replacing them, and a
    thin round is widened further before asking.

    Args:
        company: The company name.
        role: The role title.
        context: The candidate's personal context.
        location: The role's own location, from evaluate_job's extraction.
            Handed to the model both for a couple of its proposed queries and
            as context when picking among the candidates found -- appending
            it to every query was tried and measured to hurt recall, so it
            stays a minority of the attempts rather than a given.
        jd_text: The extracted job description, so fit_score is judged
            against what the role actually asks for, not just its title.

    Returns:
        The shortlist described in modes/find_contact.md, empty when no real
        profile could be found.
    """
    # The fixed queries are the proven baseline; the model's proposals run
    # alongside them rather than replacing them, so a weak or empty proposal
    # never costs the recall the fixed queries already guarantee.
    fixed, proposed = await asyncio.gather(
        _profiles(_queries(company, role)), _llm_queries(company, role, location)
    )
    found = fixed
    if proposed:
        found = await _profiles(proposed, found)
    if len(found) < MIN_CANDIDATES:
        found = await _profiles(_wider_queries(company, role), found)
    if not found:
        return Shortlist(contacts=[], reason="no linkedin.com/in/ profile matched any query")

    hits = list(found.values())[:MAX_CANDIDATES]

    pages = await asyncio.gather(*(fetch_or_empty(h.url) for h in hits))

    cv = context.profile.get("cv", {})
    system_prompt = (
        f"{load_mode('find_contact')}\n\n"
        f"## Candidate\n{cv.get('summary', '')}\n\n"
        f"## Their strongest work\n"
        + "\n".join(
            f"- {r.get('heading')}: {'; '.join(r.get('bullets', []))}"
            for r in cv.get("experience", [])
        )
    )
    location_line = f"Role location: {location}\n" if location else ""
    jd_section = f"## Job description\n{jd_text[:JD_EXCERPT_CHARS]}\n\n" if jd_text else ""
    user_prompt = (
        f"Company: {company}\nRole: {role}\n{location_line}\n"
        f"{jd_section}"
        f"## Candidate profiles found\n\n{_dossier(hits, pages)}"
    )
    result = await ask("find_contact", system_prompt, user_prompt, Shortlist)
    return result.grounded_in({h.url for h in hits})
