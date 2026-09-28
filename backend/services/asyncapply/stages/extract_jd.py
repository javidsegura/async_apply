"""Stage 1: turn a URL or pasted text into a job description. Prompt: modes/extract_jd.md."""

import asyncio

from services.asyncapply.context import load_mode
from services.asyncapply.llm import ask
from services.asyncapply.stages.utils import Extraction
from services.asyncapply.utils.web import fetch_or_empty, search

# Below this, whatever came back is a login wall or a redirect to a careers
# index, not a posting. A real Workday posting measured ~3.3k chars.
MIN_POSTING_CHARS = 400


def is_url(raw_input: str) -> bool:
    """Report whether the item is a link rather than pasted text.

    Args:
        raw_input: The item's raw input.

    Returns:
        True when it is a single http(s) URL.
    """
    stripped = raw_input.strip()
    return stripped.startswith(("http://", "https://")) and len(stripped.split()) == 1


async def _from_elsewhere(url: str) -> str:
    """Look for the same posting on another board when the link was unusable.

    Args:
        url: The original link, whose path usually names the role.

    Returns:
        The best alternative page's text, or an empty string.
    """
    slug = url.rstrip("/").split("/")[-1].replace("-", " ").replace("_", " ")
    try:
        hits = await search(f"{slug} job description")
    except RuntimeError:
        return ""

    # Fetched concurrently, not one at a time: three sequential Chromium
    # loads paid the same settle cost three times over for no reason, since
    # none of these fetches depends on another one's result.
    pages = await asyncio.gather(*(fetch_or_empty(hit.url) for hit in hits[:3]))
    return next((text for text in pages if len(text) >= MIN_POSTING_CHARS), "")


async def extract_jd(raw_input: str) -> Extraction:
    """Fetch and extract the job description behind one batch item.

    The page is rendered in a real browser, so client-side-rendered postings
    work. If the link yields nothing usable, the posting is looked for
    elsewhere before giving up.

    Args:
        raw_input: A URL or an already-pasted job description.

    Returns:
        The extraction, with `extraction_failed` set when nothing could be read.
    """
    if not is_url(raw_input):
        text = raw_input
    else:
        text = await fetch_or_empty(raw_input.strip())
        if len(text) < MIN_POSTING_CHARS:
            text = await _from_elsewhere(raw_input.strip())

    if len(text.strip()) < MIN_POSTING_CHARS:
        return Extraction(
            extraction_failed=True,
            reason=f"nothing readable at {raw_input.strip()[:120]}",
        )
    return await ask("extract_jd", load_mode("extract_jd"), text, Extraction)
