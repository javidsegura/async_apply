"""Endpoints for submitting, tracking and reading back asyncapply batches."""

import re
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import schemas
from database import get_db, models
from services.asyncapply.context import load_context
from services.asyncapply.settings import get_settings
from services.asyncapply.worker import process_batch

router = APIRouter(prefix="/asyncapply", tags=["asyncapply"])

_ASSETS = {"cv": "cv_pdf_path", "cover-letter": "cover_letter_pdf_path"}
_ASSET_LABEL = {"cv": "CV", "cover-letter": "CoverLetter"}

# What survives to build the HR-facing filename: letters and digits only, so
# a role title's punctuation and spaces can't produce a broken download name.
_NAME_PART_RE = re.compile(r"[^A-Za-z0-9]+")


def _download_filename(item: models.AsyncApplyItem, asset: str) -> str:
    """Build the filename an employer sees, distinct from where it's stored.

    The file on disk is keyed by item id so two applications never collide;
    this is what the browser offers to save it as, in the
    FirstName_LastInitial_Role_AssetType convention recruiters expect.

    Args:
        item: The item being downloaded.
        asset: "cv" or "cover-letter".

    Returns:
        A filename like "Javier_D_SoftwareEngineer_CV.pdf".
    """
    full_name = load_context().profile.get("candidate", {}).get("full_name", "")
    parts = full_name.split()
    first = _NAME_PART_RE.sub("", parts[0]) if parts else "Candidate"
    # parts[1], not parts[-1]: a Spanish two-surname name ("Javier Dominguez
    # Segura") uses the first surname professionally, and for a plain
    # "First Last" name parts[1] and parts[-1] are the same word anyway.
    last_initial = _NAME_PART_RE.sub("", parts[1])[:1] if len(parts) > 1 else ""
    role = _NAME_PART_RE.sub("", item.role or "Role")

    segments = [p for p in (first, last_initial, role, _ASSET_LABEL[asset]) if p]
    return "_".join(segments) + ".pdf"

# A company name becomes a filename, so only what survives this stays -- no
# path separators or dot-dot from a company string reaching the filesystem.
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _logo_path(company: str) -> Path:
    """Resolve a company name to its logo file, real or not yet uploaded.

    Args:
        company: The company name as stored on the item.

    Returns:
        The path a logo for this company would live at.
    """
    slug = _SLUG_RE.sub("-", company.lower()).strip("-") or "unknown"
    logos_dir = get_settings().output_dir / "logos"
    logos_dir.mkdir(parents=True, exist_ok=True)
    return logos_dir / f"{slug}.png"


@router.post("/batches", response_model=schemas.AsyncApplyBatchRead, status_code=201)
def create_batch(
    payload: schemas.AsyncApplyBatchCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> models.AsyncApplyBatch:
    """Create a batch of job postings and start processing it in the background.

    Args:
        payload: URLs or pasted job descriptions to evaluate.
        background_tasks: FastAPI's background task runner.
        db: Active database session.

    Returns:
        models.AsyncApplyBatch: The newly created batch with its queued items.

    Raises:
        HTTPException: If the payload contains no items.
    """
    if not payload.items:
        raise HTTPException(status_code=422, detail="items must not be empty")

    batch = models.AsyncApplyBatch(state="queued")
    db.add(batch)
    db.flush()

    for raw_input in payload.items:
        db.add(models.AsyncApplyItem(batch_id=batch.id, raw_input=raw_input, state="queued"))

    db.commit()
    db.refresh(batch)

    background_tasks.add_task(process_batch, batch.id)
    return batch


@router.get("/batches", response_model=list[schemas.AsyncApplyBatchRead])
def list_batches(db: Session = Depends(get_db)) -> list[models.AsyncApplyBatch]:
    """List all batches, most recent first.

    Args:
        db: Active database session.

    Returns:
        list[models.AsyncApplyBatch]: All batches.
    """
    return db.query(models.AsyncApplyBatch).order_by(models.AsyncApplyBatch.created_at.desc()).all()


@router.get("/batches/{batch_id}", response_model=schemas.AsyncApplyBatchRead)
def get_batch(batch_id: int, db: Session = Depends(get_db)) -> models.AsyncApplyBatch:
    """Fetch a batch and the current state of every item in it.

    Args:
        batch_id: Primary key of the batch.
        db: Active database session.

    Returns:
        models.AsyncApplyBatch: The batch with its items.
    """
    return _get_batch(db, batch_id)


@router.post("/batches/{batch_id}/retry", response_model=schemas.AsyncApplyBatchRead)
def retry_batch(
    batch_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> models.AsyncApplyBatch:
    """Requeue every failed item in a batch and reprocess it in the background.

    Args:
        batch_id: Primary key of the batch.
        background_tasks: FastAPI's background task runner.
        db: Active database session.

    Returns:
        models.AsyncApplyBatch: The batch with its items requeued.
    """
    batch = _get_batch(db, batch_id)

    for item in batch.items:
        if item.state == "failed":
            item.state = "queued"
            item.error = None

    batch.state = "queued"
    db.commit()
    db.refresh(batch)

    background_tasks.add_task(process_batch, batch.id)
    return batch


@router.get("/items", response_model=list[schemas.AsyncApplyItemRead])
def list_items(status: str | None = None, db: Session = Depends(get_db)) -> list[models.AsyncApplyItem]:
    """List evaluated job postings across all batches, most recent first.

    Args:
        status: Optional application status to filter by, e.g. "applied".
        db: Active database session.

    Returns:
        list[models.AsyncApplyItem]: Matching items.
    """
    query = db.query(models.AsyncApplyItem)
    if status is not None:
        query = query.filter(models.AsyncApplyItem.status == status)
    return query.order_by(models.AsyncApplyItem.created_at.desc()).all()


@router.patch("/items/{item_id}", response_model=schemas.AsyncApplyItemRead)
def update_item(
    item_id: int, payload: schemas.AsyncApplyItemUpdate, db: Session = Depends(get_db)
) -> models.AsyncApplyItem:
    """Update the hand-tracked fields on one item, such as its application status.

    Args:
        item_id: Primary key of the item.
        payload: Fields to update.
        db: Active database session.

    Returns:
        models.AsyncApplyItem: The updated item.
    """
    item = _get_item(db, item_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)) -> None:
    """Permanently delete one item, along with the PDFs it generated.

    The generated CV and cover letter are removed too: they are named after
    this item's id, so leaving them would orphan files that nothing can ever
    reach again. A missing file is not an error -- the row going away is the
    point, and a half-deleted item would be worse than a stray PDF.

    Args:
        item_id: Primary key of the item.
        db: Active database session.
    """
    item = _get_item(db, item_id)

    for attribute in _ASSETS.values():
        stored = getattr(item, attribute)
        if stored:
            Path(stored).unlink(missing_ok=True)

    db.delete(item)
    db.commit()


@router.get("/items/{item_id}/{asset}")
def download_asset(item_id: int, asset: str, db: Session = Depends(get_db)) -> FileResponse:
    """Download one item's generated CV or cover letter.

    Args:
        item_id: Primary key of the item.
        asset: Either "cv" or "cover-letter".
        db: Active database session.

    Returns:
        FileResponse: The PDF.

    Raises:
        HTTPException: If the asset name is unknown, or the PDF was never
            generated, or its file is missing from disk.
    """
    if asset not in _ASSETS:
        raise HTTPException(status_code=404, detail="unknown asset")

    item = _get_item(db, item_id)
    stored = getattr(item, _ASSETS[asset])
    if stored is None:
        raise HTTPException(status_code=404, detail=f"no {asset} was generated for this item")

    path = Path(stored)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"{asset} file is missing from disk")

    return FileResponse(
        path,
        media_type="application/pdf",
        filename=_download_filename(item, asset),
        content_disposition_type="inline",
    )


@router.put("/companies/{company}/logo")
async def upload_company_logo(company: str, file: UploadFile) -> dict:
    """Save a logo for a company, keyed by its slugified name.

    No database row is needed: the same slug that saves the file is used to
    look it up, so any item whose company matches picks it up automatically.

    Args:
        company: The company name, as it appears on the item.
        file: The uploaded image.

    Returns:
        {"ok": True} once the file is written.
    """
    path = _logo_path(company)
    path.write_bytes(await file.read())
    return {"ok": True}


@router.get("/companies/{company}/logo")
def get_company_logo(company: str) -> FileResponse:
    """Serve a company's uploaded logo, if one exists.

    Args:
        company: The company name, as it appears on the item.

    Returns:
        FileResponse: The logo image.

    Raises:
        HTTPException: 404 if no logo was uploaded for this company.
    """
    path = _logo_path(company)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="no logo uploaded for this company")
    return FileResponse(path, media_type="image/png")


def _get_batch(db: Session, batch_id: int) -> models.AsyncApplyBatch:
    """Fetch a batch by id or raise a 404.

    Args:
        db: Active database session.
        batch_id: Primary key of the batch.

    Returns:
        models.AsyncApplyBatch: The matching batch.

    Raises:
        HTTPException: If no batch with that id exists.
    """
    batch = db.get(models.AsyncApplyBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    return batch


def _get_item(db: Session, item_id: int) -> models.AsyncApplyItem:
    """Fetch an item by id or raise a 404.

    Args:
        db: Active database session.
        item_id: Primary key of the item.

    Returns:
        models.AsyncApplyItem: The matching item.

    Raises:
        HTTPException: If no item with that id exists.
    """
    item = db.get(models.AsyncApplyItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item
