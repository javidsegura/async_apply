"""Shared headless-Chromium setup for the two things that need a browser.

Fetching a page and printing a PDF both drive Chromium, so the launch, the
identity it presents and the teardown live here rather than in each caller.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from playwright.async_api import Browser, Page, async_playwright

# Playwright's default advertises "HeadlessChrome", which a number of job boards
# either block or answer with a stripped-down page. Presenting an ordinary
# desktop Chrome gets the same HTML a human would see.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
)
VIEWPORT = {"width": 1440, "height": 900}

# One Chromium process for the whole app, not one per page. Launching a fresh
# browser is the expensive part (measured: the dominant cost of processing a
# single item, once you count the JD fetch, both PDF renders and up to eight
# concurrent contact-profile fetches all doing it separately). A context is
# cheap and gives each caller isolated cookies/storage, which is the actual
# isolation a concurrent fetch needs -- the process itself doesn't need to be
# separate too.
_browser: Browser | None = None
_lock = asyncio.Lock()

# Contexts are cheap next to launching a browser, but not free: each holds a
# real renderer process's memory. Multiple users can now submit batches at
# the same time, so this caps how many pages are open across all of them at
# once -- a burst queues behind the semaphore instead of spiking RAM on a
# small box. Not measured yet at real multi-user load; tune once it's live.
MAX_CONCURRENT_PAGES = 3
_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)


async def _get_browser() -> Browser:
    """Return the shared browser, launching it once on first use.

    Returns:
        The running Chromium instance.
    """
    global _browser
    async with _lock:
        if _browser is None:
            playwright = await async_playwright().start()
            _browser = await playwright.chromium.launch(headless=True)
    return _browser


@asynccontextmanager
async def open_page() -> AsyncIterator[Page]:
    """Open a page in the shared browser and close it afterwards.

    A new context per call, not a new browser: isolated enough for concurrent
    fetches not to share cookies or storage, without paying to launch Chromium
    from scratch every time.

    Yields:
        Page: A blank page, ready to navigate or fill with content.
    """
    async with _semaphore:
        browser = await _get_browser()
        context = await browser.new_context(user_agent=USER_AGENT, viewport=VIEWPORT)
        try:
            yield await context.new_page()
        finally:
            await context.close()
