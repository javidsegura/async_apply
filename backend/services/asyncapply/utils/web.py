"""Reading the web: search without a key, and fetch pages that need JavaScript.

Both are called directly by the stages. Nothing here is exposed to the model as
a tool: what to search for and what to fetch is decided in Python, so a stage
cannot skip the lookup and invent the answer instead.
"""

import asyncio
import contextlib
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

from ddgs import DDGS

from services.asyncapply.settings import get_settings
from services.asyncapply.utils.chromium import open_page

MAX_RESULTS = 8

# Site chrome that adds noise to almost every careers page. Only elements that
# actually render need listing: inner_text already skips script, style and
# noscript. <header> is deliberately not stripped -- a few boards put the
# posting itself inside one, and losing the job beats losing a menu.
STRIP_SELECTORS = "nav, footer"

# A real posting is nowhere near this (a Workday one measured ~3.3k chars); the
# cap is for when we land on a careers index or an aggregator by mistake, so one
# page cannot crowd out the CV and profile.
MAX_PAGE_CHARS = 20_000


@dataclass
class SearchResult:
    """One search hit."""

    title: str
    url: str
    snippet: str


async def search(query: str, limit: int = MAX_RESULTS) -> list[SearchResult]:
    """Run one web search through DuckDuckGo, which needs no key or account.

    Args:
        query: The search query.
        limit: Maximum results to return.

    Returns:
        Up to `limit` results, empty when the query matched nothing.

    Raises:
        RuntimeError: if the search was refused or rate-limited, which is
            different from it finding nothing.
    """

    # ddgs is synchronous, so keep it off the loop driving the rest of the batch.
    def run() -> list[dict]:
        return list(DDGS().text(query, max_results=limit))

    try:
        rows = await asyncio.to_thread(run)
    except Exception as exc:
        # ddgs raises rather than returning an empty list when a query matches
        # nothing. That is an answer, not a failure.
        if "no results" in str(exc).lower():
            return []
        raise RuntimeError(f"search failed: {type(exc).__name__}: {exc}") from exc

    return [
        SearchResult(title=r.get("title", ""), url=r.get("href", ""), snippet=r.get("body", ""))
        for r in rows
        if r.get("href")
    ]


class BlockedUrlError(ValueError):
    """Raised for a URL that points somewhere the server must not fetch."""


def assert_fetchable(url: str) -> None:
    """Reject URLs that would make the server fetch its own infrastructure.

    The posting URL comes straight from the user, and this process renders it
    in a real browser, so without this an ordinary account could point the
    pipeline at the cloud metadata endpoint (169.254.169.254) and read the
    instance's IAM credentials out of the "job description," or sweep private
    addresses to map the internal network. Every hostname is resolved and
    every address it answers with must be publicly routable.

    This closes the straightforward case, not a determined attacker: a host
    that resolves differently between this check and the browser's own lookup
    (DNS rebinding) would still get through. Blocking that properly needs the
    fetch itself pinned to the checked address, which Chromium does not make
    easy -- worth revisiting if this ever serves untrusted signups.

    Args:
        url: The URL about to be fetched.

    Raises:
        BlockedUrlError: If the scheme is not http(s), the host cannot be
            resolved, or any resolved address is private, loopback,
            link-local, reserved, or otherwise not publicly routable.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise BlockedUrlError(f"only http(s) URLs can be fetched, got {parsed.scheme!r}")
    if not parsed.hostname:
        raise BlockedUrlError("URL has no host")

    try:
        resolved = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise BlockedUrlError(f"could not resolve {parsed.hostname}") from exc

    for info in resolved:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global or address.is_multicast:
            raise BlockedUrlError(
                f"{parsed.hostname} resolves to the non-public address {address}"
            )


async def fetch_page_text(url: str, timeout_seconds: int | None = None) -> str:
    """Load a page in headless Chromium and return its visible text.

    An ordinary HTTP fetch is not enough for most job boards: a real Workday
    posting returns ~13KB of HTML and zero visible text. This renders the page
    in the Chromium already shipped for PDFs.

    Args:
        url: The page to load.
        timeout_seconds: Budget for navigation plus settling; falls back to the
            configured fetch_timeout.

    Returns:
        The page's visible text, truncated to MAX_PAGE_CHARS.

    Raises:
        BlockedUrlError: If the URL points at non-public infrastructure.
    """
    assert_fetchable(url)
    timeout_ms = (timeout_seconds or get_settings().fetch_timeout) * 1000
    async with open_page() as page:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

        # Best-effort settle: most boards fetch the description after load, but
        # plenty never go idle (analytics, polling, video), and those shouldn't
        # cost us content that arrived seconds ago. Measured live: LinkedIn
        # never idles, so this used to burn its full budget (timeout_ms // 3,
        # up to 15s) on every single fetch for no benefit -- capped short
        # instead, since its only job is "give the page a moment," not "wait
        # as long as the whole request budget allows."
        with contextlib.suppress(Exception):
            await page.wait_for_load_state("networkidle", timeout=min(timeout_ms // 3, 3000))

        await page.evaluate(
            f"document.querySelectorAll('{STRIP_SELECTORS}').forEach(el => el.remove())"
        )
        text = await page.inner_text("body")

    return text[:MAX_PAGE_CHARS]


async def fetch_or_empty(url: str) -> str:
    """Fetch a page, returning empty text rather than raising when it fails.

    Used where one dead link among several should not lose the others.

    Args:
        url: The page to load.

    Returns:
        The page text, or an empty string if it could not be read.
    """
    try:
        return await fetch_page_text(url)
    except Exception:
        return ""
