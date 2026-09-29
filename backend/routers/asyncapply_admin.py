"""Admin-only user management: list who's using AsyncApply, their usage,
set their budget by hand, and workspace-wide time-window stats.
"""

from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db, models
from services.asyncapply.auth import require_admin

router = APIRouter(prefix="/asyncapply/admin", tags=["asyncapply-admin"])

_WINDOWS = {"7d": 7, "30d": 30, "90d": 90, "all": None}


class UserRead(BaseModel):
    """One user with their usage summary, as the admin panel lists them."""

    id: int
    email: str
    role: str
    token_budget_usd: float
    spent_usd: float
    created_at: datetime
    batch_count: int
    item_count: int
    last_active_at: datetime | None

    model_config = {"from_attributes": True}


class BudgetUpdate(BaseModel):
    """New token budget for one user, set by hand."""

    token_budget_usd: float


class BatchDetail(BaseModel):
    """One batch, as it appears in a user's drill-down history."""

    id: int
    state: str
    created_at: datetime
    item_count: int
    cost_usd: float


class UserDetail(BaseModel):
    """One user's full batch history, for the admin panel's expand view."""

    id: int
    email: str
    batches: list[BatchDetail]


class Stats(BaseModel):
    """Workspace-wide usage for one time window."""

    window: str
    active_users: int
    total_batches: int
    total_items: int
    total_spend_usd: float
    avg_cost_per_item_usd: float
    items_done: int
    items_failed: int
    items_hard_stopped: int


def _window_cutoff(window: str) -> datetime | None:
    """Resolve a window key to the cutoff datetime, or None for 'all'.

    Args:
        window: One of "7d", "30d", "90d", "all".

    Returns:
        The cutoff, or None when the window is unbounded.

    Raises:
        HTTPException: 422 if the window key isn't recognized.
    """
    if window not in _WINDOWS:
        raise HTTPException(status_code=422, detail=f"window must be one of {sorted(_WINDOWS)}")
    days = _WINDOWS[window]
    return datetime.utcnow() - timedelta(days=days) if days else None


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)
) -> list[dict]:
    """List every user with their usage summary, most recently created first."""
    rows = (
        db.query(
            models.User,
            func.count(func.distinct(models.AsyncApplyBatch.id)).label("batch_count"),
            func.count(models.AsyncApplyItem.id).label("item_count"),
            func.max(models.AsyncApplyBatch.created_at).label("last_active_at"),
        )
        .outerjoin(models.AsyncApplyBatch, models.AsyncApplyBatch.user_id == models.User.id)
        .outerjoin(models.AsyncApplyItem, models.AsyncApplyItem.batch_id == models.AsyncApplyBatch.id)
        .group_by(models.User.id)
        .order_by(models.User.created_at.desc())
        .all()
    )
    return [
        {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "token_budget_usd": user.token_budget_usd,
            "spent_usd": user.spent_usd,
            "created_at": user.created_at,
            "batch_count": batch_count,
            "item_count": item_count,
            "last_active_at": last_active_at,
        }
        for user, batch_count, item_count, last_active_at in rows
    ]


@router.get("/users/{user_id}/detail", response_model=UserDetail)
def get_user_detail(
    user_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)
) -> dict:
    """One user's full batch history, for the admin panel's drill-down.

    Raises:
        HTTPException: 404 if no such user.
    """
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    rows = (
        db.query(
            models.AsyncApplyBatch,
            func.count(models.AsyncApplyItem.id).label("item_count"),
            func.coalesce(func.sum(models.AsyncApplyItem.cost_usd), 0.0).label("cost_usd"),
        )
        .outerjoin(models.AsyncApplyItem, models.AsyncApplyItem.batch_id == models.AsyncApplyBatch.id)
        .filter(models.AsyncApplyBatch.user_id == user_id)
        .group_by(models.AsyncApplyBatch.id)
        .order_by(models.AsyncApplyBatch.created_at.desc())
        .all()
    )

    return {
        "id": user.id,
        "email": user.email,
        "batches": [
            {
                "id": batch.id,
                "state": batch.state,
                "created_at": batch.created_at,
                "item_count": item_count,
                "cost_usd": cost_usd,
            }
            for batch, item_count, cost_usd in rows
        ],
    }


@router.get("/stats", response_model=Stats)
def get_stats(
    window: str = "30d", db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)
) -> dict:
    """Workspace-wide usage for one time window -- backs both the admin
    panel's headline numbers and the time-window report.

    Args:
        window: One of "7d", "30d", "90d", "all".
    """
    cutoff = _window_cutoff(window)

    batch_query = db.query(models.AsyncApplyBatch)
    if cutoff:
        batch_query = batch_query.filter(models.AsyncApplyBatch.created_at >= cutoff)
    batch_ids = [b.id for b in batch_query.all()]

    item_query = db.query(models.AsyncApplyItem).filter(models.AsyncApplyItem.batch_id.in_(batch_ids))
    items = item_query.all() if batch_ids else []

    active_users = (
        db.query(func.count(func.distinct(models.AsyncApplyBatch.user_id)))
        .filter(models.AsyncApplyBatch.id.in_(batch_ids))
        .scalar()
        if batch_ids
        else 0
    )
    total_spend = sum(i.cost_usd or 0.0 for i in items)

    return {
        "window": window,
        "active_users": active_users or 0,
        "total_batches": len(batch_ids),
        "total_items": len(items),
        "total_spend_usd": total_spend,
        "avg_cost_per_item_usd": (total_spend / len(items)) if items else 0.0,
        "items_done": sum(1 for i in items if i.state == "done"),
        "items_failed": sum(1 for i in items if i.state == "failed"),
        "items_hard_stopped": sum(1 for i in items if i.hard_stop_reason),
    }


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
) -> None:
    """Permanently delete a user and everything they own.

    Every batch and item scoped to this user is cascade-deleted at the ORM
    level, and each item's generated CV/cover-letter PDFs are removed too --
    those are named after the item's id, so leaving them would orphan files
    nothing can ever reach again.

    Raises:
        HTTPException: 404 if no such user, 400 if the admin targets their
            own account (self-deletion would lock the workspace with no
            admin left to fix it).
    """
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="cannot delete your own admin account")

    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    for batch in user.batches:
        for item in batch.items:
            for attribute in ("cv_pdf_path", "cover_letter_pdf_path"):
                stored = getattr(item, attribute)
                if stored:
                    Path(stored).unlink(missing_ok=True)

    db.delete(user)
    db.commit()


@router.patch("/users/{user_id}/budget", response_model=UserRead)
def set_budget(
    user_id: int,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
) -> dict:
    """Set a user's token budget by hand -- the only billing mechanism for now.

    Raises:
        HTTPException: 404 if no such user, 422 if the budget is negative.
    """
    if payload.token_budget_usd < 0:
        raise HTTPException(status_code=422, detail="budget cannot be negative")

    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    user.token_budget_usd = payload.token_budget_usd
    db.commit()
    db.refresh(user)

    batch_count = db.query(func.count(models.AsyncApplyBatch.id)).filter(
        models.AsyncApplyBatch.user_id == user.id
    ).scalar()
    item_count = (
        db.query(func.count(models.AsyncApplyItem.id))
        .join(models.AsyncApplyBatch, models.AsyncApplyItem.batch_id == models.AsyncApplyBatch.id)
        .filter(models.AsyncApplyBatch.user_id == user.id)
        .scalar()
    )
    last_active_at = (
        db.query(func.max(models.AsyncApplyBatch.created_at))
        .filter(models.AsyncApplyBatch.user_id == user.id)
        .scalar()
    )

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "token_budget_usd": user.token_budget_usd,
        "spent_usd": user.spent_usd,
        "created_at": user.created_at,
        "batch_count": batch_count or 0,
        "item_count": item_count or 0,
        "last_active_at": last_active_at,
    }
