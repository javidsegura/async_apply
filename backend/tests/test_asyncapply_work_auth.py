"""A hard stop only fires from grounded facts, computed in Python -- never
written by the model as free text it can contradict."""

import pytest

from services.asyncapply.stages.evaluate_job import _hard_stop_reason
from services.asyncapply.stages.utils import CoverLetter, CvTailoring, EvaluationDraft
from services.asyncapply.stages.utils.outputs import MIN_BODY_WORDS

JD = "Senior Engineer\nUS, CA, Santa Clara\nWe are unable to sponsor work visas for this role."

def _letter(*paragraphs: str) -> CoverLetter:
    """Build a CoverLetter that clears the word floor.

    Tests care about routing and rendering, not prose length, so the given
    paragraphs are padded to satisfy MIN_BODY_WORDS rather than every test
    hand-writing 200+ words.
    """
    filler = " ".join(["detail"] * MIN_BODY_WORDS)
    return CoverLetter(paragraphs=[*paragraphs, filler])


_ASSETS = {
    "cv_tailoring": CvTailoring(projects=["A", "B"], technologies=["Python"]),
    "cover_letter": _letter("Opening."),
}


def _draft(**kwargs) -> EvaluationDraft:
    base = {
        "outside_authorized_countries": False,
        "work_auth_tier": "unstated",
        "verdict": "ok",
        **_ASSETS,
    }
    base.update(kwargs)
    return EvaluationDraft(**base)


def test_a_quoted_refusal_outside_the_authorized_countries_stops():
    draft = _draft(
        outside_authorized_countries=True,
        work_auth_tier="no_sponsorship",
        work_auth_quote="unable to sponsor work visas",
    )
    assert _hard_stop_reason(draft, JD) is not None


def test_the_quote_may_differ_in_whitespace_and_case():
    draft = _draft(
        outside_authorized_countries=True,
        work_auth_tier="no_sponsorship",
        work_auth_quote="Unable  To Sponsor\nWork Visas",
    )
    assert _hard_stop_reason(draft, JD) is not None


def test_an_inferred_refusal_not_in_the_jd_does_not_stop():
    """The live failure: the model cited a refusal that was not in the posting."""
    jd = "Senior Engineer\nUS, CA, Santa Clara\nBuild security tooling."
    draft = _draft(
        outside_authorized_countries=True,
        work_auth_tier="no_sponsorship",
        work_auth_quote="NVIDIA does not typically sponsor for this level",
    )
    assert _hard_stop_reason(draft, jd) is None


def test_no_sponsorship_inside_the_authorized_countries_does_not_stop():
    """Silence, or even a refusal, does not matter once the role is somewhere covered."""
    draft = _draft(
        outside_authorized_countries=False,
        work_auth_tier="no_sponsorship",
        work_auth_quote="unable to sponsor work visas",
    )
    assert _hard_stop_reason(draft, JD) is None


def test_unstated_outside_the_authorized_countries_does_not_stop():
    """Live batch 17: US/UK role, silence on sponsorship. Silence is never a hard-stop."""
    jd = "Software Engineer\nBased in San Francisco, CA, New York City, NY or London, UK."
    draft = _draft(outside_authorized_countries=True, work_auth_tier="unstated")
    assert _hard_stop_reason(draft, jd) is None


def test_a_grounded_citizenship_requirement_stops():
    jd = "Must be a US citizen due to government contract requirements."
    draft = _draft(
        security_clearance="citizenship_required",
        clearance_quote="Must be a US citizen",
    )
    assert _hard_stop_reason(draft, jd) is not None


def test_an_ungrounded_clearance_claim_does_not_stop():
    draft = _draft(security_clearance="clearance_required", clearance_quote="implied by the role")
    assert _hard_stop_reason(draft, JD) is None


def test_a_normal_evaluation_always_carries_assets():
    """cv_tailoring and cover_letter are required on the draft -- there is no
    conditional-on-a-stop path left for the model to skip."""
    draft = _draft()
    assert draft.cv_tailoring is not None
    assert draft.cover_letter is not None


def test_an_out_of_range_score_is_rejected():
    """Live failure: deepseek-v3.2 returned score=-10.0 on a real posting.
    That's syntactically valid float, so nothing caught it until this bound
    existed -- a wrong-but-plausible-looking score is worse than a crash,
    since it silently poisons sorting and metrics."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _draft(score=-10.0)
    with pytest.raises(ValidationError):
        _draft(score=7.0)
    _draft(score=1.0)
    _draft(score=5.0)
