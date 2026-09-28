"""Stage 2: score the job and draft the CV/cover letter. Prompt: modes/evaluate_job.md."""

import json
import re

from services.asyncapply.context import AsyncApplyContext, load_mode
from services.asyncapply.llm import ask
from services.asyncapply.stages.utils import Evaluation, EvaluationDraft


def _normalise(text: str) -> str:
    """Flatten text so a quote can be matched despite whitespace and case.

    Args:
        text: Any string taken from a posting or a model reply.

    Returns:
        The text lowercased with runs of whitespace collapsed to one space.
    """
    return re.sub(r"\s+", " ", text).strip().lower()


def _quoted(quote: str | None, jd_text: str) -> bool:
    """Report whether a claimed quote actually appears in the posting.

    Args:
        quote: The text the model cited as its evidence.
        jd_text: The posting the claim was made about.

    Returns:
        True only when the quote is real, not an inference or a paraphrase.
    """
    quote = _normalise(quote or "")
    return bool(quote) and quote in _normalise(jd_text)


def _hard_stop_reason(draft: EvaluationDraft, jd_text: str) -> str | None:
    """Decide pass/fail from the draft's grounded facts, in Python.

    The model reports facts (a tier, a clearance level, the quotes behind
    them); this is what turns those facts into a verdict. Doing it here means
    the verdict can never contradict the facts it was computed from -- the
    live failure this replaces was the model writing "...so there is no hard
    stop" and then setting the stop field anyway.

    Args:
        draft: The model's evaluation.
        jd_text: The posting it was evaluated against.

    Returns:
        Why the job is disqualified, or None.
    """
    if (
        draft.work_auth_tier == "no_sponsorship"
        and draft.outside_authorized_countries
        and _quoted(draft.work_auth_quote, jd_text)
    ):
        return f'No sponsorship, outside authorized countries: "{draft.work_auth_quote}"'

    if draft.security_clearance != "none" and _quoted(draft.clearance_quote, jd_text):
        return f'Requires {draft.security_clearance.replace("_", " ")}: "{draft.clearance_quote}"'

    return None


async def evaluate_job(jd_text: str, context: AsyncApplyContext) -> Evaluation:
    """Score one job against the candidate and draft their tailored documents.

    This is the only stage that sees the candidate's full profile, CV and writing
    style, and the only one that can set a hard stop -- decided in Python from
    the model's grounded facts, not written by the model itself.

    Args:
        jd_text: The extracted job description.
        context: The candidate's personal context.

    Returns:
        The evaluation described in modes/evaluate_job.md.
    """
    system_prompt = (
        f"{load_mode('evaluate_job')}\n\n"
        f"## Candidate profile and CV\n```json\n{json.dumps(context.profile)}\n```\n\n"
        f"## Writing style rules\n{context.voice_dna}"
    )
    draft = await ask("evaluate_job", system_prompt, jd_text, EvaluationDraft)
    reason = _hard_stop_reason(draft, jd_text)

    return Evaluation(
        company=draft.company,
        role=draft.role,
        location=draft.location,
        company_type=draft.company_type,
        score=draft.score,
        strengths=draft.strengths,
        gaps=draft.gaps,
        legitimacy=draft.legitimacy,
        work_auth_tier=draft.work_auth_tier,
        min_years_required=draft.min_years_required,
        hard_stop_reason=reason,
        verdict=draft.verdict,
        cv_tailoring=None if reason else draft.cv_tailoring,
        cover_letter=None if reason else draft.cover_letter,
    )
