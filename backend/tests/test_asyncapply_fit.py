"""Tests for trimming a CV down to the page budget."""

import pytest

from services.asyncapply.stages.utils import CvTailoring
from services.asyncapply.utils.documents import fit


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _cv(projects: int = 8, bullets: int = 5, techs: int = 37) -> dict:
    return {
        "education": [{"heading": "IE", "bullets": [f"e{i}" for i in range(4)]}],
        "experience": [{"heading": "Citi", "bullets": [f"x{i}" for i in range(bullets)]}],
        "projects": [
            {"heading": f"Project {i}", "bullets": [f"p{j}" for j in range(bullets)]}
            for i in range(projects)
        ],
        "activities": [{"heading": "Student Gov", "bullets": ["a0", "a1", "a2"]}],
        "awards": [{"heading": f"Award {i}", "text": "won it"} for i in range(3)],
        "technologies": [f"tech{i}" for i in range(techs)],
    }


def _profile(**kw) -> dict:
    return {"candidate": {"full_name": "Ada"}, "cv": _cv(**kw)}


def _fake_page(measure):
    """Build an open_page replacement backed by the given height function."""

    class _Page:
        async def set_viewport_size(self, size):
            self.viewport = size

        async def emulate_media(self, media):
            self.media = media

        async def set_content(self, html):
            self._html = html

        async def evaluate(self, script):
            return await measure(self._html)

    class _Ctx:
        async def __aenter__(self):
            return _Page()

        async def __aexit__(self, *exc):
            return False

    return lambda: _Ctx()


def _heights(values: list[int]):
    """Fake a page reporting each height in turn, so no browser is needed."""
    state = {"n": 0}

    async def measure(html: str) -> int:
        value = values[min(state["n"], len(values) - 1)]
        state["n"] += 1
        return value

    return measure, state


def test_house_style_matches_the_reference_cv() -> None:
    """The reference CV is 2 projects, 1 education bullet, 17 technologies."""
    cv = _cv()

    fit._apply_house_style(cv)

    assert len(cv["projects"]) == 2
    assert len(cv["technologies"]) == 17
    assert len(cv["education"][0]["bullets"]) == 1
    assert len(cv["experience"][0]["bullets"]) == 4
    assert all(len(p["bullets"]) <= 2 for p in cv["projects"])


def test_drop_last_keeps_at_least_one_entry() -> None:
    cv = _cv(projects=2)

    assert fit._drop_last(cv, "projects") is True
    assert fit._drop_last(cv, "projects") is False
    assert len(cv["projects"]) == 1


def test_dropping_an_entry_is_a_last_resort() -> None:
    """Shortening a list costs the reader less than losing a whole entry."""
    first_drop = next(i for i, (kind, _) in enumerate(fit.CUTS) if kind == "drop")

    assert first_drop >= 3


@pytest.mark.anyio
async def test_a_page_that_already_fits_is_only_house_styled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    measure, state = _heights([fit.PAGE_PX - 10])
    monkeypatch.setattr(fit, "open_page", _fake_page(measure))

    await fit.fit_cv(_profile(), CvTailoring())

    assert state["n"] == 1  # measured once, cut nothing further


@pytest.mark.anyio
async def test_it_cuts_until_it_fits(monkeypatch: pytest.MonkeyPatch) -> None:
    measure, state = _heights([1400, 1200, fit.PAGE_PX - 5])
    monkeypatch.setattr(fit, "open_page", _fake_page(measure))

    await fit.fit_cv(_profile(), CvTailoring())

    assert state["n"] == 3


@pytest.mark.anyio
async def test_it_gives_up_rather_than_looping_forever(monkeypatch: pytest.MonkeyPatch) -> None:
    """A page that cannot be made to fit must still return, not spin."""
    measure, state = _heights([5000])
    monkeypatch.setattr(fit, "open_page", _fake_page(measure))

    assert await fit.fit_cv(_profile(), CvTailoring())
    assert state["n"] < 50


@pytest.mark.anyio
async def test_the_callers_profile_is_never_mutated(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rendering must not quietly edit the profile held by the batch."""
    measure, _ = _heights([5000])  # always over, so every cut runs
    monkeypatch.setattr(fit, "open_page", _fake_page(measure))
    profile = _profile()

    await fit.fit_cv(profile, CvTailoring(projects=["Project 3"]))

    assert len(profile["cv"]["projects"]) == 8
    assert len(profile["cv"]["technologies"]) == 37
    assert len(profile["cv"]["education"][0]["bullets"]) == 4


@pytest.mark.anyio
async def test_the_chosen_project_leads(monkeypatch: pytest.MonkeyPatch) -> None:
    """The model's pick decides which projects survive the two-project cap."""
    captured = {}

    def spy(profile, **kwargs):
        captured["projects"] = [p["heading"] for p in profile["cv"]["projects"]]
        return "<html></html>"

    measure, _ = _heights([fit.PAGE_PX - 10])
    monkeypatch.setattr(fit, "open_page", _fake_page(measure))
    monkeypatch.setattr(fit, "build_cv", spy)

    await fit.fit_cv(_profile(), CvTailoring(projects=["Project 5", "Project 2"]))

    assert captured["projects"] == ["Project 5", "Project 2"]


@pytest.mark.anyio
async def test_height_is_measured_at_the_print_width(monkeypatch: pytest.MonkeyPatch) -> None:
    """Measuring at the screen width under-reports: print wraps text far more."""
    seen = {}
    measure, _ = _heights([fit.PAGE_PX - 10])
    page_factory = _fake_page(measure)

    class _Ctx:
        async def __aenter__(self):
            self.page = await page_factory().__aenter__()
            return self.page

        async def __aexit__(self, *exc):
            seen["viewport"] = self.page.viewport
            seen["media"] = self.page.media
            return False

    monkeypatch.setattr(fit, "open_page", lambda: _Ctx())

    await fit.fit_cv(_profile(), CvTailoring())

    assert seen["viewport"]["width"] == fit.PRINT_WIDTH_PX
    assert seen["media"] == "print"


@pytest.mark.anyio
async def test_two_projects_survive_a_page_that_never_fits(monkeypatch: pytest.MonkeyPatch) -> None:
    """The house style is a floor, not a cap that can be cut under pressure:
    the CV must never end up showing one project just to save vertical space."""
    captured = {}

    def spy(profile, **kwargs):
        captured["projects"] = len(profile["cv"]["projects"])
        return "<html></html>"

    monkeypatch.setattr(fit, "build_cv", spy)
    measure, state = _heights([5000])  # never fits, so every cut runs including "give up"
    monkeypatch.setattr(fit, "open_page", _fake_page(measure))

    await fit.fit_cv(_profile(), CvTailoring())

    assert captured["projects"] == 2
    assert state["n"] < 50


@pytest.mark.anyio
async def test_the_font_shrinks_before_a_project_would_need_to_go(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    def spy(profile, base_font_pt=10.5, line_height=1.25, **kwargs):
        captured["font_pt"] = base_font_pt
        return "<html></html>"

    monkeypatch.setattr(fit, "build_cv", spy)
    measure, _ = _heights([5000])
    monkeypatch.setattr(fit, "open_page", _fake_page(measure))

    await fit.fit_cv(_profile(), CvTailoring())

    assert captured["font_pt"] < 10.5
    assert captured["font_pt"] >= fit.MIN_FONT_PT
