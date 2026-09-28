"""Read/write access to what shapes an AsyncApply run.

profile and agent-dna are per-user, stored on the users row -- everyone edits
their own. The stage prompts and pipeline settings (which model runs each
stage, parallelism, timeouts) are shared across every user of this
deployment, so only the admin can change them.
"""

import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, models
from services.asyncapply.auth import get_current_user, require_admin
from services.asyncapply.context.loader import MODES_DIR
from services.asyncapply.profile_extraction import extract_profile_from_cv
from services.asyncapply.profile_schema import ExtractedProfile, Profile, profile_from_dict, profile_to_dict
from services.asyncapply.settings import AVAILABLE_MODELS, get_or_create_row

router = APIRouter(prefix="/asyncapply/config", tags=["asyncapply-config"])


class ContentPayload(BaseModel):
    """Raw text in, raw text out -- used for every editable text config."""

    content: str


class SettingsPayload(BaseModel):
    """The full pipeline settings row. PUT always replaces every field."""

    model_extract_jd: str
    model_evaluate_job: str
    model_find_contact: str
    parallelism: int
    max_attempts: int
    stage_timeout: int
    fetch_timeout: int
    cv_max_pages: int
    output_dir: str | None = None


# Mode names are used to build a file path, so they are checked against the
# actual files on disk rather than trusted from the URL -- there is no other
# way for a user-supplied string to become a filesystem path in this router.
_MODE_NAME_RE = re.compile(r"^[a-z_]+$")


@router.get("/profile", response_model=Profile)
def get_profile(user: models.User = Depends(get_current_user)) -> Profile:
    """Read the current user's profile as structured form data.

    Returns:
        The profile, defaulted to an empty shell if nothing was saved yet --
        so a brand-new user's form has every section ready to fill in
        rather than erroring on a missing profile.
    """
    return profile_from_dict(user.profile if isinstance(user.profile, dict) else {})


@router.put("/profile", response_model=Profile)
def update_profile(
    payload: Profile,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> Profile:
    """Save the current user's profile from the form.

    Pydantic has already validated the shape by the time this runs, so
    there is no invalid-YAML failure mode left the way the old raw-text
    editor had -- the form can't produce a document the worker can't read.
    """
    user.profile = profile_to_dict(payload)
    db.commit()
    return payload


@router.post("/profile/from-cv", response_model=ExtractedProfile)
async def fill_profile_from_cv(
    file: UploadFile, _user: models.User = Depends(get_current_user)
) -> ExtractedProfile:
    """Best-effort fill of the profile form from an uploaded CV.

    Returns the extraction only -- it is not saved. The form merges these
    values into whatever the user has already typed and lets them review
    and correct everything before saving for real.

    Raises:
        HTTPException: 422 if the file isn't readable as a PDF.
    """
    try:
        return await extract_profile_from_cv(await file.read())
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"could not read this CV: {exc}") from exc


@router.get("/agent-dna")
def get_agent_dna(user: models.User = Depends(get_current_user)) -> dict:
    """Read the current user's agent DNA."""
    return {"content": user.agent_dna_md or ""}


@router.put("/agent-dna")
def update_agent_dna(
    payload: ContentPayload,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> dict:
    """Overwrite the current user's agent DNA. Free-form, nothing to validate."""
    user.agent_dna_md = payload.content
    db.commit()
    return {"content": payload.content}


@router.get("/modes")
def list_modes(_admin: models.User = Depends(require_admin)) -> list[str]:
    """List the stage prompt names available to read and edit. Admin only."""
    return sorted(p.stem for p in MODES_DIR.glob("*.md"))


@router.get("/modes/{name}")
def get_mode(name: str, _admin: models.User = Depends(require_admin)) -> dict:
    """Read one stage prompt's raw text. Admin only.

    Raises:
        HTTPException: 404 if the name is not a real mode file.
    """
    path = _mode_path(name)
    return {"content": path.read_text() if path.exists() else ""}


@router.put("/modes/{name}")
def update_mode(
    name: str, payload: ContentPayload, _admin: models.User = Depends(require_admin)
) -> dict:
    """Overwrite one stage prompt. Admin only, free-form markdown.

    Raises:
        HTTPException: 404 if the name is not an existing mode file -- this
            endpoint edits prompts that already exist, it does not create new
            stages, since a new stage needs code to call it regardless.
    """
    path = _mode_path(name, must_exist=True)
    path.write_text(payload.content)
    return {"content": payload.content}


@router.get("/available-models")
def available_models(_user: models.User = Depends(get_current_user)) -> list[str]:
    """The curated model options the settings UI may pick from per stage."""
    return AVAILABLE_MODELS


@router.get("/settings")
def get_pipeline_settings(
    db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)
) -> dict:
    """Read the live pipeline settings: models per stage, and the tuning knobs. Admin only.

    The API key and base URL are never included here -- they stay in env
    vars, since a settings table any authenticated user could read is not
    where a key belongs.
    """
    return _settings_dict(get_or_create_row(db))


@router.put("/settings")
def update_pipeline_settings(
    payload: SettingsPayload,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
) -> dict:
    """Update the pipeline settings. Admin only. Takes effect on the next batch.

    Raises:
        HTTPException: 422 if a chosen model isn't one of the curated options.
    """
    for field in ("model_extract_jd", "model_evaluate_job", "model_find_contact"):
        model = getattr(payload, field)
        if model not in AVAILABLE_MODELS:
            raise HTTPException(status_code=422, detail=f"{model!r} is not one of the offered models")

    row = get_or_create_row(db)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit()
    return _settings_dict(row)


def _settings_dict(row) -> dict:
    """Serialize a settings row the same shape the UI reads and writes.

    Args:
        row: The AsyncApplySettings DB row.

    Returns:
        Its fields as a plain dict.
    """
    return {
        "model_extract_jd": row.model_extract_jd,
        "model_evaluate_job": row.model_evaluate_job,
        "model_find_contact": row.model_find_contact,
        "parallelism": row.parallelism,
        "max_attempts": row.max_attempts,
        "stage_timeout": row.stage_timeout,
        "fetch_timeout": row.fetch_timeout,
        "cv_max_pages": row.cv_max_pages,
        "output_dir": row.output_dir,
    }


def _mode_path(name: str, *, must_exist: bool = False):
    """Resolve a mode name to its file, rejecting anything that isn't one.

    Args:
        name: The mode name from the URL.
        must_exist: Whether the file must already exist on disk.

    Returns:
        The resolved path.

    Raises:
        HTTPException: 404 if the name is not a plain lowercase identifier,
            or must_exist is set and no such file exists.
    """
    if not _MODE_NAME_RE.match(name):
        raise HTTPException(status_code=404, detail="no such mode")
    path = MODES_DIR / f"{name}.md"
    if must_exist and not path.exists():
        raise HTTPException(status_code=404, detail="no such mode")
    return path
