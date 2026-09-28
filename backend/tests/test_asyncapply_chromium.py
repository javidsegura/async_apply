"""One Chromium process is shared across every open_page() call, not
relaunched each time -- launching fresh was the dominant cost of processing
a single item once every fetch and PDF render did it separately."""

import asyncio

import pytest

from services.asyncapply.utils import chromium


class FakePage:
    pass


class FakeContext:
    def __init__(self):
        self.closed = False

    async def new_page(self):
        return FakePage()

    async def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self):
        self.contexts_created = 0

    async def new_context(self, **kwargs):
        self.contexts_created += 1
        return FakeContext()


class FakePlaywright:
    def __init__(self, browser):
        self.chromium = self
        self._browser = browser

    async def launch(self, headless=True):
        return self._browser


class FakeDriver:
    """Stands in for async_playwright(), whose real .start() launches the driver."""

    def __init__(self, start):
        self.start = start


@pytest.fixture(autouse=True)
def reset_singleton():
    """The module-level browser must not leak between tests."""
    chromium._browser = None
    yield
    chromium._browser = None


@pytest.fixture
def anyio_backend():
    return "asyncio"


pytestmark = pytest.mark.anyio


async def test_the_browser_is_launched_once_across_many_open_page_calls(monkeypatch):
    browser = FakeBrowser()
    launch_count = 0

    async def fake_start():
        nonlocal launch_count
        launch_count += 1
        return FakePlaywright(browser)

    monkeypatch.setattr(chromium, "async_playwright", lambda: FakeDriver(fake_start))

    for _ in range(5):
        async with chromium.open_page():
            pass

    assert launch_count == 1
    assert browser.contexts_created == 5


async def test_concurrent_open_page_calls_still_launch_only_one_browser(monkeypatch):
    """The lock must hold under real concurrency, not just sequential calls."""
    browser = FakeBrowser()
    launch_count = 0

    async def fake_start():
        nonlocal launch_count
        await asyncio.sleep(0.01)  # widen the race window
        launch_count += 1
        return FakePlaywright(browser)

    monkeypatch.setattr(chromium, "async_playwright", lambda: FakeDriver(fake_start))

    async def use_a_page():
        async with chromium.open_page():
            pass

    await asyncio.gather(*(use_a_page() for _ in range(8)))

    assert launch_count == 1
    assert browser.contexts_created == 8


async def test_each_call_gets_its_own_context_and_it_is_closed_after(monkeypatch):
    browser = FakeBrowser()
    contexts = []

    async def fake_start():
        return FakePlaywright(browser)

    real_new_context = browser.new_context

    async def tracked_new_context(**kwargs):
        ctx = await real_new_context(**kwargs)
        contexts.append(ctx)
        return ctx

    browser.new_context = tracked_new_context
    monkeypatch.setattr(chromium, "async_playwright", lambda: FakeDriver(fake_start))

    async with chromium.open_page():
        pass

    assert len(contexts) == 1
    assert contexts[0].closed is True
