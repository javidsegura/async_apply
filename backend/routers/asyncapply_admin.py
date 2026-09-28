"""Admin-only user management: list who's using AsyncApply, set their budget.

Minimal on purpose -- this is what create_batch's budget check needs to be
usable at all, ahead of the fuller admin usage panel (peer activity stats,
time-window reports) that comes later.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, models
from services.asyncapply.auth import require_admin

router = APIRouter(prefix="/asyncapply/admin", tags=["asyncapply-admin"])


class UserRead(BaseModel):
    """One user, as the admin panel lists them."""

    id: int
    email: str
    role: str
    token_budget_usd: float
    spent_usd: float
    created_at: datetime

    model_config = {"from_attributes": True}


class BudgetUpdate(BaseModel):
    """New token budget for one user, set by hand."""

    token_budget_usd: float


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)
) -> list[models.User]:
    """List every user, most recently created first."""
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


@router.patch("/users/{user_id}/budget", response_model=UserRead)
def set_budget(
    user_id: int,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
) -> models.User:
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
    return user
