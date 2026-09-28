"""Trims a CV until it fits the page budget.

Capping one field is not enough on its own: measured on a real profile, cutting
technologies from 37 to 20 saves 17px while the page is 400px over, and how much
each cut saves depends on how the text wraps. So this renders, measures, applies
the next cut and measures again.

Cuts are ordered least-damaging first: shortening a list costs the reader less
than losing a whole entry.
"""

from copy import deepcopy

from services.asyncapply.stages.utils import CvTailoring
from services.asyncapply.utils.chromium import open_page
from services.asyncapply.utils.documents.aliases import apply_aliases
from services.asyncapply.utils.documents.html import build_cv, choose_projects

# The template prints on Letter with 0.5in vertical and 0.6in horizontal
# margins. Height must be measured at the *print* width: the screen viewport is
# far wider, so text wraps less and the page measures shorter than it prints.
PAGE_PX = 10 * 96
PRINT_WIDTH_PX = round(7.3 * 96)

# The shape of the reference CV, applied to every render so output is
# consistent rather than a function of how much the profile happens to hold.
# (section, bullets-per-entry) for the fixed sections, plus the list caps.
HOUSE_STYLE_BULLETS = {"education": 1, "experience": 4, "projects": 2, "activities": 2}
HOUSE_STYLE_TECHNOLOGIES = 17
HOUSE_STYLE_PROJECTS = 2

# Two projects is the house style, not a maximum to trim away under pressure:
# a smaller page reads better than a candidate who apparently ships one thing.
# So there is no ("drop", "projects") cut -- the last resorts are shrinking the
# font and, only past that, dropping awards.
MIN_FONT_PT = 9.0
FONT_STEP_PT = 0.5

CUTS = [
    ("technologies", 12),
    ("bullets", ("projects", 1)),
    ("bullets", ("experience", 3)),
    ("bullets", ("activities", 1)),
    ("font", None),
    ("font", None),
    ("font", None),
    ("bullets", ("experience", 2)),
    ("drop", "awards"),
]


def _cap_bullets(cv: dict, section: str, limit: int) -> bool:
    """Shorten the bullet list on every entry in one section.

    Args:
        cv: The `cv` section of the profile, edited in place.
        section: Which section to shorten.
        limit: Bullets to keep per entry.

    Returns:
        True if anything was removed.
    """
    trimmed = False
    for entry in cv.get(section, []):
        if len(entry.get("bullets", [])) > limit:
            entry["bullets"] = entry["bullets"][:limit]
            trimmed = True
    return trimmed


def _drop_last(cv: dict, section: str) -> bool:
    """Drop the last entry of a section, keeping at least one.

    Args:
        cv: The `cv` section of the profile, edited in place.
        section: Which section to shorten.

    Returns:
        True if an entry was dropped.
    """
    entries = cv.get(section, [])
    if len(entries) <= 1:
        return False
    entries.pop()
    return True


class FitState:
    """Everything one fit_cv run mutates: the profile's cv section, and the
    body font size once every content cut has already run once."""

    def __init__(self, cv: dict, font_pt: float, line_height: float):
        self.cv = cv
        self.font_pt = font_pt
        self.line_height = line_height

    def shrink_font(self) -> bool:
        """Step the font down by FONT_STEP_PT, keeping line-height in ratio.

        Returns:
            True if the font was still above MIN_FONT_PT and got smaller.
        """
        if self.font_pt <= MIN_FONT_PT:
            return False
        ratio = self.line_height / self.font_pt
        self.font_pt -= FONT_STEP_PT
        self.line_height = round(self.font_pt * ratio, 3)
        return True


def _apply(state: "FitState", cut: tuple) -> bool:
    """Run one cut.

    Args:
        state: The fit run's mutable cv section and current font size.
        cut: A (kind, argument) pair from CUTS.

    Returns:
        True if the cut removed anything or shrank the font further.
    """
    kind, arg = cut
    if kind == "font":
        return state.shrink_font()
    cv = state.cv
    if kind == "technologies":
        technologies = cv.get("technologies", [])
        if len(technologies) <= arg:
            return False
        del technologies[arg:]
        return True
    if kind == "bullets":
        return _cap_bullets(cv, *arg)
    return _drop_last(cv, arg)


def _apply_house_style(cv: dict) -> None:
    """Cut the CV to the reference shape before any measuring happens.

    Args:
        cv: The `cv` section of the profile, edited in place.
    """
    for section, limit in HOUSE_STYLE_BULLETS.items():
        _cap_bullets(cv, section, limit)
    del cv.get("technologies", [])[HOUSE_STYLE_TECHNOLOGIES:]
    del cv.get("projects", [])[HOUSE_STYLE_PROJECTS:]


async def fit_cv(
    profile: dict, tailoring: CvTailoring, max_pages: int = 1, jd_text: str | None = None
) -> str:
    """Build the CV HTML, trimming until it fits the page budget.

    The profile is copied first, so rendering never edits the caller's data.

    Args:
        profile: The candidate's parsed profile.
        tailoring: Which projects to show, and the technologies order.
        max_pages: How many pages the CV may occupy.
        jd_text: The posting text. When a listed technology has a known alias
            (Go/Golang, K8s/Kubernetes) and the posting uses the other
            spelling, that spelling is appended so a literal-matching ATS
            catches it -- nothing is added that is not already on the list.

    Returns:
        The HTML, trimmed as far as needed and no further.
    """
    profile = deepcopy(profile)
    cv = profile.setdefault("cv", {})
    budget = PAGE_PX * max_pages

    # Resolve the model's choices into the profile itself, so from here on there
    # is one thing to trim rather than two, and build_cv can render it plainly.
    if tailoring.technologies:
        cv["technologies"] = list(tailoring.technologies)
    if jd_text:
        cv["technologies"] = apply_aliases(cv.get("technologies", []), jd_text)
    cv["projects"] = choose_projects(cv, tailoring.projects)
    _apply_house_style(cv)

    state = FitState(cv, font_pt=10.5, line_height=1.25)

    def render() -> str:
        return build_cv(profile, base_font_pt=state.font_pt, line_height=state.line_height)

    async with open_page() as page:
        await page.set_viewport_size({"width": PRINT_WIDTH_PX, "height": PAGE_PX})
        await page.emulate_media(media="print")

        async def too_tall(html: str) -> bool:
            await page.set_content(html)
            return await page.evaluate("document.documentElement.scrollHeight") > budget

        html = render()
        while await too_tall(html):
            # Every cut strictly shrinks the page, so this ends: either it fits,
            # or nothing is left to remove.
            if not any(_apply(state, cut) for cut in CUTS):
                break
            html = render()

    return html

