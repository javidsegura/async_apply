"""Public lead capture for the marketing site's /pricing page.

No auth: visitors picking a plan haven't signed in yet. There is no real
checkout behind this -- a submission just records a row so the founder can
follow up by hand (Zelle/PayPal). See routers/asyncapply_admin.py for the
admin-read side.
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db, models
from services.asyncapply.auth import require_admin

router = APIRouter(tags=["leads"])


class LeadCreate(BaseModel):
    """A visitor's plan pick from the pricing page.

    Lengths are capped because this endpoint is unauthenticated: without a
    bound, a script could write arbitrarily large rows into the table.
    """

    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    plan: str = Field(min_length=1, max_length=60)


class LeadRead(BaseModel):
    """One recorded lead, as the admin panel would list it."""

    id: int
    name: str
    email: str
    plan: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/leads", response_model=LeadRead)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)) -> models.PricingLead:
    """Record a pricing-page lead.

    Args:
        payload: The visitor's name, email, and chosen plan.
        db: Active database session.

    Returns:
        The stored lead row.
    """
    lead = models.PricingLead(name=payload.name, email=payload.email, plan=payload.plan)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/admin/leads", response_model=list[LeadRead])
def list_leads(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)) -> list[models.PricingLead]:
    """List every pricing-page lead, newest first. Admin only.

    Args:
        db: Active database session.
        _admin: The authenticated admin (unused beyond gating access).

    Returns:
        All recorded leads, newest first.
    """
    return db.query(models.PricingLead).order_by(models.PricingLead.created_at.desc()).all()
