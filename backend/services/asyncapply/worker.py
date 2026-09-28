"""Runs a batch: every queued item through the three stages, recording progress in the DB."""

import asyncio
from datetime import datetime

from sqlalchemy.orm import Session

from database import SessionLocal, models
from services.asyncapply import stages
from services.asyncapply.context import AsyncApplyContext, load_context
from services.asyncapply.llm import track_usage
from services.asyncapply.settings import AsyncApplySettings, get_settings
from services.asyncapply.stages.extract_jd import is_url
from services.asyncapply.stages.utils import Evaluation
from services.asyncapply.utils import documents


def recover_orphaned_work() -> None:
    """Fail any batch or item left mid-flight by a previous process.

    Processing runs as an in-memory FastAPI BackgroundTask, not a persisted
    job queue: a container restart (a redeploy, a crash) kills it without a
    trace, leaving the row at "queued" or "running" forever with nothing left
    that will ever pick it up again -- silently stuck, not failed, so it
    never shows up as something to retry. Called once at startup, before
    anything new is submitted, so a restart can't leave work invisibly
    hanging: it is marked failed instead, with a reason that says why, and
    the existing retry-failed-items endpoint takes it from there.
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        items = (
            db.query(models.AsyncApplyItem)
            .filter(models.AsyncApplyItem.state.in_(["queued", "running"]))
            .all()
        )
        for item in items:
            item.state = "failed"
            item.error = "interrupted by a server restart"
            item.ended_at = now

        batches = (
            db.query(models.AsyncApplyBatch)
            .filter(models.AsyncApplyBatch.state.in_(["queued", "running"]))
            .all()
        )
        for batch in batches:
            _finalize(db, batch)
    finally:
        db.close()


async def process_batch(batch_id: int) -> None:
    """Process every queued item in a batch, respecting the parallelism setting.

    Runs as a FastAPI background task, so it owns its own DB session rather than
    reusing the request-scoped one. The batch is always moved out of "running"
    before returning, so a failure can never wedge it there.

    Args:
        batch_id: The asyncapply_batches.id to process.
    """
    settings = get_settings()
    db = SessionLocal()
    try:
        batch = db.get(models.AsyncApplyBatch, batch_id)
        if batch is None:
            return

        batch.state = "running"
        batch.started_at = datetime.utcnow()
        batch.ended_at = None
        db.commit()

        item_ids = [item.id for item in batch.items if item.state == "queued"]

        try:
            context = load_context()
        except (FileNotFoundError, OSError) as exc:
            # Nothing can be evaluated without the candidate's context, so fail
            # every item with the same reason instead of rediscovering it N times.
            _fail_all(db, item_ids, f"context unavailable: {exc}")
            _finalize(db, batch)
            return

        semaphore = asyncio.Semaphore(settings.parallelism)

        async def run_one(item_id: int) -> None:
            async with semaphore:
                await _process_item(item_id, context, settings)

        async with asyncio.TaskGroup() as task_group:
            for item_id in item_ids:
                task_group.create_task(run_one(item_id))

        db.refresh(batch)
        _finalize(db, batch)
    finally:
        db.close()


def _fail_all(db: Session, item_ids: list[int], error: str) -> None:
    """Mark every listed item failed with a shared error message.

    Args:
        db: Active database session.
        item_ids: Primary keys of the items to fail.
        error: The error message to record on each.
    """
    now = datetime.utcnow()
    for item_id in item_ids:
        item = db.get(models.AsyncApplyItem, item_id)
        if item is not None:
            item.state = "failed"
            item.error = error
            item.ended_at = now
    db.commit()


def _finalize(db: Session, batch: models.AsyncApplyBatch) -> None:
    """Close out a batch with a state that reflects how its items actually went.

    "done" has to mean everything worked, otherwise the batch state alone can
    never tell you something needs attention: a single dead link in a batch of
    twenty would read as success.

    Args:
        db: Active database session.
        batch: The batch to finalize.
    """
    states = {item.state for item in batch.items}
    if states == {"failed"}:
        batch.state = "failed"
    elif "failed" in states:
        batch.state = "partial"
    else:
        batch.state = "done"

    batch.ended_at = datetime.utcnow()
    db.commit()


async def _process_item(item_id: int, context: AsyncApplyContext, settings: AsyncApplySettings) -> None:
    """Run one item through the stages and record its outcome.

    This is the task boundary for a batch: it catches every exception so one bad
    posting is recorded as a failed item instead of tearing down the task group
    and leaving the rest of the batch unprocessed.

    Args:
        item_id: The asyncapply_items.id to process.
        context: The candidate's personal context, shared across the batch.
        settings: Resolved settings for this batch.
    """
    db = SessionLocal()
    try:
        item = db.get(models.AsyncApplyItem, item_id)
        if item is None:
            return

        item.state = "running"
        item.started_at = datetime.utcnow()
        item.error = None
        db.commit()

        try:
            with track_usage() as usage:
                await _run_stages(item, context, settings, db)
            item.state = "done"
        except Exception as exc:
            db.rollback()
            item = db.get(models.AsyncApplyItem, item_id)
            item.state = "failed"
            item.error = f"{type(exc).__name__}: {exc}"
        finally:
            # Recorded even on failure: a stage can burn real tokens before erroring.
            item.total_tokens = usage.total_tokens
            item.cost_usd = usage.total_cost_usd

        item.ended_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


async def _run_stages(
    item: models.AsyncApplyItem,
    context: AsyncApplyContext,
    settings: AsyncApplySettings,
    db: Session,
) -> None:
    """The three stages for one item, left to raise on failure.

    Assets and contact lookup are best-effort: a PDF or contact that fails must
    not cost us the evaluation itself, which is already saved by then.

    Args:
        item: The item being processed, mutated in place.
        context: The candidate's personal context.
        settings: Resolved settings for this batch.
        db: Active database session.
    """
    # Every error message below is prefixed with the stage it came from. The
    # worker doesn't otherwise track progress at that granularity, and the
    # frontend's per-item pipeline view reads these prefixes to show which
    # stage actually failed rather than guessing.
    try:
        extraction = await stages.extract_jd(item.raw_input)
        if extraction.extraction_failed:
            raise ValueError(extraction.reason or "no reason given")
        if not extraction.jd_text:
            raise ValueError("no jd_text returned")
    except Exception as exc:
        raise RuntimeError(f"extraction failed: {exc}") from exc
    item.url = item.raw_input.strip() if is_url(item.raw_input) else None

    try:
        evaluation = await stages.evaluate_job(extraction.jd_text, context)
    except Exception as exc:
        raise RuntimeError(f"evaluation failed: {type(exc).__name__}: {exc}") from exc
    _save_evaluation(item, evaluation)
    db.commit()

    if item.hard_stop_reason:
        return

    # Neither depends on the other's result, only on the evaluation both
    # already have, so they run concurrently rather than one after the other
    # -- each is mostly waiting on Chromium or the network, not CPU, so there
    # is no real contention running them side by side.
    async def render_assets_step() -> str | None:
        try:
            await _render_assets(item, context, settings, evaluation, extraction.jd_text)
            return None
        except Exception as exc:
            return f"asset generation failed: {type(exc).__name__}: {exc}"

    async def find_contact_step() -> str | None:
        try:
            shortlist = await stages.find_contact(
                item.company or "",
                item.role or "",
                context,
                location=evaluation.location,
                jd_text=extraction.jd_text,
            )
            item.contacts = [c.model_dump() for c in shortlist.contacts]
            if shortlist.contacts:
                # The flat columns carry the best target, so the common case
                # stays a single read; the rest lives in `contacts`.
                best = shortlist.contacts[0]
                item.contact_name = best.contact_name
                item.contact_message = best.message
            return None
        except Exception as exc:
            return f"contact lookup failed: {type(exc).__name__}: {exc}"

    errors = await asyncio.gather(render_assets_step(), find_contact_step())
    item.error = "; ".join(e for e in errors if e) or None
    db.commit()


def _save_evaluation(item: models.AsyncApplyItem, evaluation: Evaluation) -> None:
    """Copy the evaluation onto the item.

    Args:
        item: The item being processed, mutated in place.
        evaluation: What the evaluate_job stage returned.
    """
    item.company = evaluation.company
    item.role = evaluation.role
    item.location = evaluation.location
    item.company_type = evaluation.company_type
    item.score = evaluation.score
    item.verdict = evaluation.verdict
    item.strengths = evaluation.strengths
    item.gaps = evaluation.gaps
    item.legitimacy = evaluation.legitimacy
    item.work_auth_tier = evaluation.work_auth_tier
    item.min_years_required = evaluation.min_years_required
    item.hard_stop_reason = evaluation.hard_stop_reason
    item.status = "hard_stopped" if evaluation.hard_stop_reason else "evaluated"


async def _render_assets(
    item: models.AsyncApplyItem,
    context: AsyncApplyContext,
    settings: AsyncApplySettings,
    evaluation: Evaluation,
    jd_text: str,
) -> None:
    """Render the tailored CV and cover letter PDFs for one item.

    Args:
        item: The item being processed, mutated with the output paths.
        context: The candidate's personal context.
        settings: Resolved settings, providing the output directory.
        evaluation: The evaluation, carrying cv_tailoring and cover_letter.
        jd_text: The posting text, so the CV can add a technology's alternate
            spelling when the posting uses one the profile does not.
    """
    slug = f"{item.id}-{(item.company or 'company').lower().replace(' ', '-')}"

    if evaluation.cv_tailoring:
        cv_html = await documents.fit_cv(
            context.profile, evaluation.cv_tailoring, max_pages=settings.cv_max_pages, jd_text=jd_text
        )
        path = await documents.render_pdf(cv_html, settings.output_dir / f"{slug}-cv.pdf")
        item.cv_pdf_path = str(path)

    if evaluation.cover_letter:
        cover_html = documents.build_cover_letter(
            context.profile, item.role or "", item.company or "", evaluation.cover_letter
        )
        path = await documents.render_pdf(cover_html, settings.output_dir / f"{slug}-cover.pdf")
        item.cover_letter_pdf_path = str(path)

