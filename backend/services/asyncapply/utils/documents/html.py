"""Builds the CV and cover-letter HTML.

Everything factual comes from profile.yml. The model contributes only which
projects appear and how the technologies list is ordered, so there is no path
by which it can put an employer, a date or a metric on the page.

Text is escaped where each value is built rather than at substitution time,
which is what lets the builders emit real list markup instead of escaped tags.
"""

import html
import unicodedata
from datetime import date
from pathlib import Path

from services.asyncapply.context.loader import TEMPLATES_DIR
from services.asyncapply.stages.utils import CoverLetter, CvTailoring

CV_TEMPLATE = TEMPLATES_DIR / "cv_template.html"
COVER_LETTER_TEMPLATE = TEMPLATES_DIR / "cover_letter_template.html"

LINKS = {"linkedin": "LinkedIn", "github": "Github", "portfolio_url": "Portfolio"}

# Punctuation that PDF text extraction mangles for ATS parsers.
_UNICODE_REPLACEMENTS = {
    "—": "-",
    "–": "-",
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
}


def ats_normalize(text: str) -> str:
    """Replace unicode punctuation that ATS parsers mis-read.

    Args:
        text: Raw text destined for a PDF.

    Returns:
        Text with dashes, smart quotes and ellipses reduced to ASCII, and
        zero-width characters stripped.
    """
    for source, replacement in _UNICODE_REPLACEMENTS.items():
        text = text.replace(source, replacement)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cf")


def _text(value: object) -> str:
    """Normalize and escape one plain-text value.

    Args:
        value: Any scalar destined for the template; falsy becomes "".

    Returns:
        ATS-normalized, HTML-escaped text safe to drop into markup.
    """
    return html.escape(ats_normalize(str(value))) if value else ""


def _render(template_path: Path, mapping: dict[str, str]) -> str:
    """Substitute every {{PLACEHOLDER}} in a template.

    Args:
        template_path: Path to the .html template.
        mapping: Placeholder name (without braces) to replacement markup.

    Returns:
        The filled-in HTML. A placeholder the mapping misses stays visible as
        {{NAME}}, which a test catches rather than it silently vanishing.
    """
    template = template_path.read_text()
    for key, value in mapping.items():
        template = template.replace(f"{{{{{key}}}}}", value)
    return template


def _entry(entry: dict) -> str:
    """Render one CV entry from the profile.

    Two shapes are supported, matching what a CV actually needs: a one-line
    entry (an award) written as `text`, or a block with a location, dates and
    bullets (a job, a degree, a project).

    Args:
        entry: A profile entry with `heading` plus either `text` or any of
            `subheading` / `location` / `dates` / `bullets`.

    Returns:
        The entry markup.
    """
    heading = _text(entry.get("heading"))

    if summary := entry.get("text"):
        prefix = f"<b>{heading}</b> - " if heading else ""
        return f'<p class="entry">{prefix}{_text(summary)}</p>'

    rows = f'<div class="row"><span class="left">{heading}</span>' \
           f'<span class="right">{_text(entry.get("location"))}</span></div>'
    if entry.get("subheading") or entry.get("dates"):
        rows += f'<div class="row sub"><span class="left">{_text(entry.get("subheading"))}</span>' \
                f'<span class="right">{_text(entry.get("dates"))}</span></div>'
    if bullets := entry.get("bullets"):
        rows += "<ul>" + "".join(f"<li>{_text(b)}</li>" for b in bullets) + "</ul>"
    return rows


def _section(entries: list[dict]) -> str:
    """Render a whole CV section.

    Args:
        entries: The section's entries, in the order they should appear.

    Returns:
        The section markup, or "" when there are no entries.
    """
    return "".join(_entry(e) for e in entries or [])


def choose_projects(cv: dict, headings: list[str]) -> list[dict]:
    """Pick the profile's projects the model asked for, in its order.

    Matching is forgiving about a shortened heading, since a model that writes
    "FlowGentic" for "FlowGentic (HPC middleware)" means the same project. A
    heading matching nothing real is simply skipped.

    Args:
        cv: The `cv` section of profile.yml.
        headings: Project headings the model chose, best first.

    Returns:
        The matching profile entries. Falls back to the profile's own order
        when the model chose nothing usable.
    """
    projects = cv.get("projects", [])
    chosen = []
    for wanted in headings:
        name = wanted.strip().lower()
        match = next(
            (p for p in projects
             if (h := str(p.get("heading", "")).lower()) and (h == name or h.startswith(name)
                                                              or name.startswith(h))),
            None,
        )
        if match is not None and match not in chosen:
            chosen.append(match)
    return chosen or projects


def _contact_line(candidate: dict) -> str:
    """Build the phone | email | links line under the name.

    Args:
        candidate: The `candidate` section of profile.yml.

    Returns:
        Markup joining whichever contact details exist.
    """
    parts = []
    if phone := candidate.get("phone"):
        parts.append(_text(phone))
    if email := candidate.get("email"):
        parts.append(f'<a href="mailto:{_text(email)}">{_text(email)}</a>')
    parts += [
        f'<a href="{_text(candidate[key])}">{label}</a>'
        for key, label in LINKS.items()
        if candidate.get(key)
    ]
    return " | ".join(parts)


def build_cv(
    profile: dict,
    tailoring: CvTailoring | None = None,
    *,
    base_font_pt: float = 10.5,
    line_height: float = 1.25,
) -> str:
    """Render a CV to HTML.

    Args:
        profile: The candidate's parsed profile.yml.
        tailoring: Which projects to show and the technologies order. Omit
            when the caller (fit_cv) has already resolved these into
            profile["cv"] itself; passing it here would apply the choice a
            second time.
        base_font_pt: Body font size. fit_cv shrinks this before it drops a
            whole section, since a smaller page reads better than a missing
            project.
        line_height: Body line height, shrunk in step with the font.

    Returns:
        The filled-in CV HTML.
    """
    candidate = profile.get("candidate", {})
    cv = profile.get("cv", {})

    if tailoring is not None:
        projects = choose_projects(cv, tailoring.projects)
        technologies = tailoring.technologies or cv.get("technologies", [])
    else:
        projects = cv.get("projects", [])
        technologies = cv.get("technologies", [])

    return _render(
        CV_TEMPLATE,
        {
            "NAME": _text(candidate.get("full_name")),
            "LOCATION": _text(candidate.get("location")),
            "CONTACT_LINE": _contact_line(candidate),
            "BASE_FONT_SIZE": f"{base_font_pt:g}",
            "LINE_HEIGHT": f"{line_height:g}",
            "WORK_PERMITS": _text(cv.get("work_permits")),
            "EDUCATION": _section(cv.get("education", [])),
            "EXPERIENCE": _section(cv.get("experience", [])),
            "PROJECTS": _section(projects),
            "AWARDS": _section(cv.get("awards", [])),
            "ACTIVITIES": _section(cv.get("activities", [])),
            "LANGUAGES": _text(cv.get("languages")),
            "TECHNOLOGIES": _text(", ".join(technologies)),
        },
    )


def build_cover_letter(profile: dict, role_title: str, company: str, letter: CoverLetter) -> str:
    """Render the cover letter to HTML.

    Args:
        profile: The candidate's parsed profile.yml.
        role_title: The role being applied to.
        company: The hiring company.
        letter: The letter body the model wrote.

    Returns:
        The filled-in cover letter HTML.
    """
    candidate = profile.get("candidate", {})

    return _render(
        COVER_LETTER_TEMPLATE,
        {
            "NAME": _text(candidate.get("full_name")),
            "CONTACT_LINE": _contact_line(candidate),
            "DATE": _text(date.today().strftime("%d %B %Y")),
            "COMPANY": _text(company),
            "ROLE_TITLE": _text(role_title),
            "BODY": "".join(f"<p>{_text(p)}</p>" for p in letter.paragraphs if p and p.strip()),
        },
    )
