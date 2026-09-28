"""Tests for services.asyncapply.worker: DB state transitions with the pipeline stages mocked out."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, models
from services.asyncapply import worker
from services.asyncapply.context import AsyncApplyContext
from services.asyncapply.stages.utils import Evaluation, Extraction, Shortlist


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def db_session_factory(monkeypatch: pytest.MonkeyPatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(worker, "SessionLocal", TestingSessionLocal)
    return TestingSessionLocal


def _make_batch(session_factory, raw_inputs: list[str]) -> int:
    db = session_factory()
    batch = models.AsyncApplyBatch(state="queued")
    db.add(batch)
    db.flush()
    for raw_input in raw_inputs:
        db.add(models.AsyncApplyItem(batch_id=batch.id, raw_input=raw_input, state="queued"))
    db.commit()
    batch_id = batch.id
    db.close()
    return batch_id


@pytest.mark.anyio
async def test_process_batch_marks_hard_stopped_item_done_without_assets(
    db_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    batch_id = _make_batch(db_session_factory, ["https://example.com/job"])

    monkeypatch.setattr(worker, "load_context", lambda: AsyncApplyContext(profile={}, voice_dna=""))
    monkeypatch.setattr(
        worker.stages, "extract_jd", _async_return(Extraction(extraction_failed=False, jd_text="JD"))
    )
    monkeypatch.setattr(
        worker.stages,
        "evaluate_job",
        _async_return(Evaluation(company="Acme", role="Eng", score=2.0, hard_stop_reason="no sponsorship")),
    )

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("should not run find_contact or asset generation on a hard stop")

    monkeypatch.setattr(worker.stages, "find_contact", fail_if_called)

    await worker.process_batch(batch_id)

    db = db_session_factory()
    batch = db.get(models.AsyncApplyBatch, batch_id)
    assert batch.state == "done"
    item = batch.items[0]
    assert item.state == "done"
    assert item.hard_stop_reason == "no sponsorship"
    assert item.cv_pdf_path is None
    assert item.contact_name is None


@pytest.mark.anyio
async def test_process_batch_marks_extraction_failure_as_failed(
    db_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    batch_id = _make_batch(db_session_factory, ["https://example.com/dead-link"])

    monkeypatch.setattr(worker, "load_context", lambda: AsyncApplyContext(profile={}, voice_dna=""))
    monkeypatch.setattr(
        worker.stages, "extract_jd", _async_return(Extraction(extraction_failed=True, reason="404"))
    )

    await worker.process_batch(batch_id)

    db = db_session_factory()
    batch = db.get(models.AsyncApplyBatch, batch_id)
    assert batch.state == "failed"
    item = batch.items[0]
    assert item.state == "failed"
    assert "404" in item.error


@pytest.mark.anyio
async def test_process_item_records_exception_as_error(db_session_factory, monkeypatch: pytest.MonkeyPatch) -> None:
    batch_id = _make_batch(db_session_factory, ["broken input"])

    monkeypatch.setattr(worker, "load_context", lambda: AsyncApplyContext(profile={}, voice_dna=""))

    async def boom(*args, **kwargs):
        raise ValueError("agent returned garbage")

    monkeypatch.setattr(worker.stages, "extract_jd", boom)

    await worker.process_batch(batch_id)

    db = db_session_factory()
    item = db.get(models.AsyncApplyBatch, batch_id).items[0]
    assert item.state == "failed"
    assert "agent returned garbage" in item.error


@pytest.mark.anyio
async def test_extraction_failure_is_tagged_by_stage(db_session_factory, monkeypatch: pytest.MonkeyPatch) -> None:
    """The frontend's pipeline view reads this prefix to know which stage
    actually failed, so it has to survive being re-wrapped."""
    batch_id = _make_batch(db_session_factory, ["broken input"])
    monkeypatch.setattr(worker, "load_context", lambda: AsyncApplyContext(profile={}, voice_dna=""))

    async def boom(*args, **kwargs):
        raise ValueError("no route to page")

    monkeypatch.setattr(worker.stages, "extract_jd", boom)
    await worker.process_batch(batch_id)

    item = db_session_factory().get(models.AsyncApplyBatch, batch_id).items[0]
    assert "extraction failed" in item.error


@pytest.mark.anyio
async def test_evaluation_failure_is_tagged_by_stage(
    db_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    batch_id = _make_batch(db_session_factory, ["https://a.com/job"])
    monkeypatch.setattr(worker, "load_context", lambda: AsyncApplyContext(profile={}, voice_dna=""))
    monkeypatch.setattr(
        worker.stages, "extract_jd", _async_return(Extraction(extraction_failed=False, jd_text="JD"))
    )

    async def boom(*args, **kwargs):
        raise ValueError("provider timed out")

    monkeypatch.setattr(worker.stages, "evaluate_job", boom)
    await worker.process_batch(batch_id)

    item = db_session_factory().get(models.AsyncApplyBatch, batch_id).items[0]
    assert "evaluation failed" in item.error


@pytest.mark.anyio
async def test_one_failing_item_does_not_stop_the_rest_of_the_batch(
    db_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unexpected error on one item must not tear down the whole task group."""
    batch_id = _make_batch(db_session_factory, ["good", "bad"])

    monkeypatch.setattr(worker, "load_context", lambda: AsyncApplyContext(profile={}, voice_dna=""))

    async def extract(raw_input: str, **kwargs):
        if raw_input == "bad":
            raise KeyError("unexpected shape")
        return Extraction(extraction_failed=False, jd_text="JD")

    monkeypatch.setattr(worker.stages, "extract_jd", extract)
    monkeypatch.setattr(
        worker.stages,
        "evaluate_job",
        _async_return(Evaluation(company="Acme", role="Eng", hard_stop_reason="capped")),
    )

    await worker.process_batch(batch_id)

    db = db_session_factory()
    batch = db.get(models.AsyncApplyBatch, batch_id)
    states = {item.raw_input: item.state for item in batch.items}
    assert states == {"good": "done", "bad": "failed"}
    # Some worked, some didn't: "done" would hide that one needs attention.
    assert batch.state == "partial"
    assert batch.ended_at is not None


@pytest.mark.anyio
async def test_missing_context_fails_items_without_wedging_the_batch(
    db_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    batch_id = _make_batch(db_session_factory, ["https://example.com/job"])

    def no_context():
        raise FileNotFoundError("profile.yml is missing")

    monkeypatch.setattr(worker, "load_context", no_context)

    await worker.process_batch(batch_id)

    db = db_session_factory()
    batch = db.get(models.AsyncApplyBatch, batch_id)
    assert batch.state == "failed"
    assert batch.ended_at is not None
    assert "profile.yml is missing" in batch.items[0].error


def _async_return(value):
    """Build an async function that always returns the given value."""

    async def fn(*args, **kwargs):
        return value

    return fn


@pytest.mark.anyio
async def test_full_evaluation_is_persisted_to_sql(
    db_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The full evaluation must be persisted, not just the headline fields."""
    batch_id = _make_batch(db_session_factory, ["https://example.com/job"])

    monkeypatch.setattr(worker, "load_context", lambda: AsyncApplyContext(profile={}, voice_dna=""))
    monkeypatch.setattr(
        worker.stages,
        "extract_jd",
        _async_return(Extraction(extraction_failed=False, jd_text="JD")),
    )
    monkeypatch.setattr(
        worker.stages,
        "evaluate_job",
        _async_return(
            Evaluation(
                company="Acme",
                role="Backend Engineer",
                company_type="scale_up",
                score=4.0,
                verdict="Strong match.",
                strengths=["python", "fastapi"],
                gaps=["kubernetes"],
                legitimacy="high_confidence",
                work_auth_tier="unstated",
                hard_stop_reason=None,
            )
        ),
    )
    monkeypatch.setattr(worker.stages, "find_contact", _async_return(Shortlist(contacts=[], reason="none")))

    async def no_assets(*args, **kwargs):
        return None

    monkeypatch.setattr(worker, "_render_assets", no_assets)

    await worker.process_batch(batch_id)

    db = db_session_factory()
    item = db.get(models.AsyncApplyBatch, batch_id).items[0]
    assert item.state == "done"
    assert item.url == "https://example.com/job"
    assert item.company == "Acme"
    assert item.company_type == "scale_up"
    assert item.strengths == ["python", "fastapi"]
    assert item.gaps == ["kubernetes"]
    assert item.legitimacy == "high_confidence"
    assert item.work_auth_tier == "unstated"
    assert item.status == "evaluated"


@pytest.mark.anyio
async def test_hard_stopped_item_gets_hard_stopped_status(
    db_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    batch_id = _make_batch(db_session_factory, ["https://example.com/job"])

    monkeypatch.setattr(worker, "load_context", lambda: AsyncApplyContext(profile={}, voice_dna=""))
    monkeypatch.setattr(
        worker.stages, "extract_jd", _async_return(Extraction(extraction_failed=False, jd_text="JD"))
    )
    monkeypatch.setattr(
        worker.stages,
        "evaluate_job",
        _async_return(Evaluation(company="Acme", role="Eng", hard_stop_reason="no sponsorship")),
    )

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("must not run after a hard stop")

    monkeypatch.setattr(worker.stages, "find_contact", fail_if_called)

    await worker.process_batch(batch_id)

    db = db_session_factory()
    item = db.get(models.AsyncApplyBatch, batch_id).items[0]
    assert item.status == "hard_stopped"
    assert item.cv_pdf_path is None


@pytest.mark.anyio
async def test_all_items_succeeding_is_done_not_partial(
    db_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    batch_id = _make_batch(db_session_factory, ["a", "b"])

    monkeypatch.setattr(worker, "load_context", lambda: AsyncApplyContext(profile={}, voice_dna=""))
    monkeypatch.setattr(
        worker.stages, "extract_jd", _async_return(Extraction(extraction_failed=False, jd_text="JD"))
    )
    monkeypatch.setattr(
        worker.stages,
        "evaluate_job",
        _async_return(Evaluation(company="Acme", role="Eng", hard_stop_reason="capped")),
    )

    await worker.process_batch(batch_id)

    db = db_session_factory()
    assert db.get(models.AsyncApplyBatch, batch_id).state == "done"


@pytest.mark.anyio
async def test_recover_orphaned_work_fails_stuck_items_and_finalizes_batches(
    db_session_factory,
) -> None:
    """A container restart kills the in-memory BackgroundTask mid-batch,
    leaving rows at queued/running with nothing left to ever finish them."""
    db = db_session_factory()
    batch = models.AsyncApplyBatch(state="running")
    db.add(batch)
    db.flush()
    stuck = models.AsyncApplyItem(batch_id=batch.id, raw_input="a", state="running")
    still_queued = models.AsyncApplyItem(batch_id=batch.id, raw_input="b", state="queued")
    already_done = models.AsyncApplyItem(batch_id=batch.id, raw_input="c", state="done")
    db.add_all([stuck, still_queued, already_done])
    db.commit()
    batch_id, stuck_id, queued_id, done_id = batch.id, stuck.id, still_queued.id, already_done.id
    db.close()

    worker.recover_orphaned_work()

    db = db_session_factory()
    assert db.get(models.AsyncApplyItem, stuck_id).state == "failed"
    assert db.get(models.AsyncApplyItem, stuck_id).error == "interrupted by a server restart"
    assert db.get(models.AsyncApplyItem, queued_id).state == "failed"
    assert db.get(models.AsyncApplyItem, done_id).state == "done"  # untouched
    assert db.get(models.AsyncApplyBatch, batch_id).state == "partial"


@pytest.mark.anyio
async def test_recover_orphaned_work_leaves_finished_batches_alone(db_session_factory) -> None:
    db = db_session_factory()
    batch = models.AsyncApplyBatch(state="done")
    db.add(batch)
    db.flush()
    db.add(models.AsyncApplyItem(batch_id=batch.id, raw_input="a", state="done"))
    db.commit()
    batch_id = batch.id
    db.close()

    worker.recover_orphaned_work()

    assert db_session_factory().get(models.AsyncApplyBatch, batch_id).state == "done"


@pytest.mark.anyio
async def test_asset_and_contact_errors_both_surface_when_both_fail(
    db_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The two steps run concurrently, so a failure in one must not hide a
    failure in the other -- both messages should reach the item."""
    batch_id = _make_batch(db_session_factory, ["https://a.com/job"])
    monkeypatch.setattr(worker, "load_context", lambda: AsyncApplyContext(profile={}, voice_dna=""))
    monkeypatch.setattr(
        worker.stages, "extract_jd", _async_return(Extraction(extraction_failed=False, jd_text="JD"))
    )
    monkeypatch.setattr(
        worker.stages,
        "evaluate_job",
        _async_return(Evaluation(company="Acme", role="Eng", score=3.0)),
    )

    async def boom_assets(*args, **kwargs):
        raise ValueError("chromium unreachable")

    async def boom_contact(*args, **kwargs):
        raise ValueError("search backend down")

    monkeypatch.setattr(worker, "_render_assets", boom_assets)
    monkeypatch.setattr(worker.stages, "find_contact", boom_contact)

    await worker.process_batch(batch_id)

    item = db_session_factory().get(models.AsyncApplyBatch, batch_id).items[0]
    assert item.state == "done"  # best-effort steps don't fail the item
    assert "asset generation failed" in item.error
    assert "contact lookup failed" in item.error


@pytest.mark.anyio
async def test_assets_and_contact_lookup_run_concurrently(
    db_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    batch_id = _make_batch(db_session_factory, ["https://a.com/job"])
    monkeypatch.setattr(worker, "load_context", lambda: AsyncApplyContext(profile={}, voice_dna=""))
    monkeypatch.setattr(
        worker.stages, "extract_jd", _async_return(Extraction(extraction_failed=False, jd_text="JD"))
    )
    monkeypatch.setattr(
        worker.stages,
        "evaluate_job",
        _async_return(Evaluation(company="Acme", role="Eng", score=3.0)),
    )

    started_together = asyncio.Event()
    both_started = []

    async def slow_assets(*args, **kwargs):
        both_started.append("assets")
        if len(both_started) == 2:
            started_together.set()
        await asyncio.wait_for(started_together.wait(), timeout=1)

    async def slow_contact(*args, **kwargs):
        both_started.append("contact")
        if len(both_started) == 2:
            started_together.set()
        await asyncio.wait_for(started_together.wait(), timeout=1)
        return Shortlist(contacts=[])

    monkeypatch.setattr(worker, "_render_assets", slow_assets)
    monkeypatch.setattr(worker.stages, "find_contact", slow_contact)

    await worker.process_batch(batch_id)

    item = db_session_factory().get(models.AsyncApplyBatch, batch_id).items[0]
    assert item.state == "done"
    assert item.error is None
