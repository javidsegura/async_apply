"""Pydantic request and response schemas for the AsyncApply API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AsyncApplyBatchCreate(BaseModel):
    """One or more URLs / pasted job descriptions to evaluate as a batch."""

    items: list[str]


class AsyncApplyItemRead(BaseModel):
    """One job posting's evaluation and progress through the pipeline."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    raw_input: str
    state: str
    url: str | None
    company: str | None
    role: str | None
    location: str | None = None
    company_type: str | None
    score: float | None
    verdict: str | None
    strengths: list[str] | None
    gaps: list[str] | None
    legitimacy: str | None
    work_auth_tier: str | None
    min_years_required: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None
    hard_stop_reason: str | None
    cv_pdf_path: str | None
    cover_letter_pdf_path: str | None
    contact_name: str | None
    contact_message: str | None
    contacts: list[dict] | None = None
    status: str
    error: str | None
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None


class AsyncApplyItemUpdate(BaseModel):
    """Hand-edited application tracking fields."""

    status: str | None = None


class AsyncApplyBatchRead(BaseModel):
    """A batch and the state of every item in it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    state: str
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None
    items: list[AsyncApplyItemRead]
