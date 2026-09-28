"""Tests for the HTML building and ATS normalization in services.asyncapply.utils.documents."""

from services.asyncapply.stages.utils.outputs import MIN_BODY_WORDS
from services.asyncapply.stages.utils import CoverLetter, CvTailoring
from services.asyncapply.utils.documents import html as render_html

PROFILE = {
    "candidate": {
        "full_name": "Ada Lovelace",
        "location": "Madrid, Spain",
        "email": "ada@example.com",
        "phone": "600",
        "linkedin": "https://li/ada",
    },
    "cv": {
        "work_permits": "EU authorized",
        "languages": "Spanish (Native)",
        "technologies": ["Python", "SQL"],
        "education": [
            {
                "heading": "IE University",
                "location": "Madrid",
                "subheading": "BSc CS",
                "dates": "2027",
                "bullets": ["GPA 93/100"],
            }
        ],
        "experience": [
            {
                "heading": "Citi",
                "subheading": "SWE Intern",
                "location": "Warsaw",
                "dates": "2026",
                "bullets": ["Built X", "Shipped Y"],
            }
        ],
        "projects": [
            {"heading": "Zeffo", "bullets": ["Event-driven"]},
            {"heading": "FlowGentic", "bullets": ["HPC middleware"]},
        ],
        "awards": [{"heading": "EduCaixa", "text": "Finalist."}],
        "activities": [
            {"heading": "Student Gov", "subheading": "Rep", "dates": "2023",
             "bullets": ["Drove curriculum change"]}
        ],
    },
}


# Padding so fixtures clear the cover letter word floor; these tests are
# about rendering, not prose length.
_FILLER = " ".join(["detail"] * MIN_BODY_WORDS)


def _tailoring(**kw) -> CvTailoring:
    return CvTailoring(**kw)


# --- ATS normalization -----------------------------------------------------


def test_ats_normalize_replaces_smart_punctuation() -> None:
    normalized = render_html.ats_normalize("State–of–the–art — end–to–end… “fast”")

    assert "–" not in normalized
    assert "—" not in normalized
    assert "…" not in normalized
    assert "“" not in normalized
    assert "..." in normalized


def test_ats_normalize_strips_zero_width_characters() -> None:
    assert render_html.ats_normalize("hello​world") == "helloworld"


# --- the CV ----------------------------------------------------------------


def test_every_factual_section_comes_from_the_profile() -> None:
    result = render_html.build_cv(PROFILE, _tailoring())

    assert "Ada Lovelace" in result and "Madrid, Spain" in result
    assert "EU authorized" in result
    assert "IE University" in result and "GPA 93/100" in result
    assert "Citi" in result and "Warsaw" in result
    assert "Student Gov" in result


def test_experience_bullets_render_as_markup() -> None:
    result = render_html.build_cv(PROFILE, _tailoring())

    assert "<li>Built X</li>" in result
    assert "&lt;ul&gt;" not in result


def test_bullet_text_is_escaped_but_the_list_markup_is_not() -> None:
    """The regression that once printed literal <ul> tags into every PDF."""
    profile = {
        **PROFILE,
        "cv": {**PROFILE["cv"],
               "experience": [{"heading": "Citi", "bullets": ["Cut p95 <200ms & held it"]}]},
    }

    result = render_html.build_cv(profile, _tailoring())

    assert "<ul><li>" in result
    assert "&lt;200ms" in result and "&amp;" in result
    assert "&lt;ul&gt;" not in result


def test_an_entry_with_text_renders_as_one_line() -> None:
    """Awards are a name and a sentence, not a heading with bullets."""
    result = render_html.build_cv(PROFILE, _tailoring())

    assert "<b>EduCaixa</b> - Finalist." in result


def test_the_model_chooses_which_projects_appear() -> None:
    result = render_html.build_cv(PROFILE, _tailoring(projects=["FlowGentic"]))

    assert "FlowGentic" in result
    assert "Zeffo" not in result


def test_an_invented_project_falls_back_to_the_profile() -> None:
    """A heading matching nothing real must not blank the section."""
    result = render_html.build_cv(PROFILE, _tailoring(projects=["Totally Made Up"]))

    assert "Zeffo" in result and "Totally Made Up" not in result


def test_technologies_keep_the_models_ordering() -> None:
    """The ordering is the ATS signal, so it must survive to the page."""
    result = render_html.build_cv(PROFILE, _tailoring(technologies=["Kubernetes", "Go"]))

    assert "Kubernetes, Go" in result


def test_technologies_fall_back_to_the_profile_when_the_model_returns_none() -> None:
    result = render_html.build_cv(PROFILE, _tailoring(technologies=[]))

    assert "Python, SQL" in result


def test_no_tailoring_renders_the_profile_as_is() -> None:
    """fit_cv resolves choices into the profile itself, then calls build_cv with
    no tailoring at all -- this is the contract that path relies on."""
    result = render_html.build_cv(PROFILE)

    assert "Python, SQL" in result  # cv.technologies, unreordered
    assert "Zeffo" in result and "FlowGentic" in result  # cv.projects, both


def test_no_placeholder_is_left_unfilled() -> None:
    assert "{{" not in render_html.build_cv(PROFILE, _tailoring())


def test_contact_line_skips_missing_details() -> None:
    result = render_html.build_cv({"candidate": {"full_name": "Ada", "email": "a@b.c"}, "cv": {}},
                                  _tailoring())

    assert "a@b.c" in result
    assert "Github" not in result


# --- the cover letter ------------------------------------------------------


def test_cover_letter_renders_the_body_and_fixed_header() -> None:
    result = render_html.build_cover_letter(
        PROFILE, "Backend Engineer", "Acme",
        CoverLetter(paragraphs=["I am applying.", "I shipped X, cutting latency 40%.", _FILLER]),
    )

    # Fixed by the template, never written by the model.
    assert "Ada Lovelace" in result
    assert "Dear Hiring Team," in result and "Sincerely," in result
    assert "Acme" in result and "Backend Engineer" in result
    # The body is the model's prose, one <p> per paragraph.
    assert "<p>I am applying.</p>" in result
    assert "cutting latency 40%" in result
    assert "{{" not in result


def test_cover_letter_skips_blank_paragraphs() -> None:
    result = render_html.build_cover_letter(
        PROFILE, "Eng", "Acme", CoverLetter(paragraphs=["Real.", "   ", "", _FILLER])
    )

    assert result.count("<p>Real.</p>") == 1
    assert "<p></p>" not in result
