"""SQLAlchemy ORM models for AsyncApply."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base


class AsyncApplySettings(Base):
    """Singleton row (id=1) holding the pipeline's tunable configuration.

    Secrets (the API key, the base URL) stay in env vars, never here.
    """

    __tablename__ = "asyncapply_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    model_extract_jd: Mapped[str] = mapped_column(String, nullable=False)
    model_evaluate_job: Mapped[str] = mapped_column(String, nullable=False)
    model_find_contact: Mapped[str] = mapped_column(String, nullable=False)
    parallelism: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    stage_timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    fetch_timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=45)
    cv_max_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    output_dir: Mapped[str | None] = mapped_column(String, nullable=True)


class AsyncApplyBatch(Base):
    """A batch of job postings submitted together for pipeline processing."""

    __tablename__ = "asyncapply_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    items: Mapped[list["AsyncApplyItem"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class AsyncApplyItem(Base):
    """One job posting (URL or pasted text) and everything the pipeline learned about it.

    This is the system of record for an application: the evaluation, the drafted
    outreach and the paths to the generated PDFs all live here.
    """

    __tablename__ = "asyncapply_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("asyncapply_batches.id"), nullable=False)
    raw_input: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False, default="queued")

    # Evaluation
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    company: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    company_type: Mapped[str | None] = mapped_column(String, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String, nullable=True)
    strengths: Mapped[list | None] = mapped_column(JSON, nullable=True)
    gaps: Mapped[list | None] = mapped_column(JSON, nullable=True)
    legitimacy: Mapped[str | None] = mapped_column(String, nullable=True)
    work_auth_tier: Mapped[str | None] = mapped_column(String, nullable=True)
    min_years_required: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hard_stop_reason: Mapped[str | None] = mapped_column(String, nullable=True)

    # Generated assets
    cv_pdf_path: Mapped[str | None] = mapped_column(String, nullable=True)
    cover_letter_pdf_path: Mapped[str | None] = mapped_column(String, nullable=True)

    # Outreach
    contact_name: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_message: Mapped[str | None] = mapped_column(String, nullable=True)
    contacts: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Tracking the application itself, updated by hand after the pipeline runs.
    status: Mapped[str] = mapped_column(String, nullable=False, default="evaluated")

    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    batch: Mapped["AsyncApplyBatch"] = relationship(back_populates="items")
