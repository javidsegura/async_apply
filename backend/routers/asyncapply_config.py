"""Read/write access to everything that shapes the AsyncApply pipeline:
profile.yml, voice_dna.md, the stage prompts in context/modes, and the
pipeline settings row (model per stage, parallelism, timeouts).
"""

import re

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from services.asyncapply.context.loader import MODES_DIR, USER_DIR
from services.asyncapply.settings import AVAILABLE_MODELS, get_or_create_row

router = APIRouter(prefix="/asyncapply/config", tags=["asyncapply-config"])


class ContentPayload(BaseModel):
    """Raw text in, raw text out -- used for every editable config file."""

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


PROFILE_PATH = USER_DIR / "profile.yml"
VOICE_DNA_PATH = USER_DIR / "voice_dna.md"

# Mode names are used to build a file path, so they are checked against the
# actual files on disk rather than trusted from the URL -- there is no other
# way for a user-supplied string to become a filesystem path in this router.
_MODE_NAME_RE = re.compile(r"^[a-z_]+$")


def _read(path) -> dict:
    """Read one config file's raw text.

    Args:
        path: The file to read.

    Returns:
        {"content": the file's text, or "" if it does not exist yet}.
    """
    return {"content": path.read_text() if path.exists() else ""}


def _write_text(path, content: str) -> dict:
    """Write one config file's raw text, no parsing.

    Args:
        path: The file to write.
        content: The new contents.

    Returns:
        {"content": what was written}.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return {"content": content}


def _write_yaml(path, content: str) -> dict:
    """Write profile.yml, refusing anything that would not load back.

    A bad edit here is not cosmetic -- load_context() reads this file before
    every single batch, so a syntax error or a non-mapping document would take
    the whole pipeline down on the next submission. Validating before writing
    means the file on disk is never worse than what was already there.

    Args:
        path: The file to write.
        content: The proposed new YAML text.

    Returns:
        {"content": what was written}.

    Raises:
        HTTPException: 422 if the YAML does not parse to a mapping.
    """
    try:
        parsed = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=422, detail=f"invalid YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="profile.yml must be a YAML mapping")
    return _write_text(path, content)


@router.get("/profile")
def get_profile() -> dict:
    """Read profile.yml as raw text, for the editor to load into a textarea."""
    return _read(PROFILE_PATH)


@router.put("/profile")
def update_profile(payload: ContentPayload) -> dict:
    """Overwrite profile.yml after validating it parses as a YAML mapping."""
    return _write_yaml(PROFILE_PATH, payload.content)


@router.get("/voice-dna")
def get_voice_dna() -> dict:
    """Read voice_dna.md as raw text."""
    return _read(VOICE_DNA_PATH)


@router.put("/voice-dna")
def update_voice_dna(payload: ContentPayload) -> dict:
    """Overwrite voice_dna.md. Free-form prose, nothing to validate."""
    return _write_text(VOICE_DNA_PATH, payload.content)


@router.get("/modes")
def list_modes() -> list[str]:
    """List the stage prompt names available to read and edit."""
    return sorted(p.stem for p in MODES_DIR.glob("*.md"))


@router.get("/modes/{name}")
def get_mode(name: str) -> dict:
    """Read one stage prompt's raw text.

    Raises:
        HTTPException: 404 if the name is not a real mode file.
    """
    path = _mode_path(name)
    return _read(path)


@router.put("/modes/{name}")
def update_mode(name: str, payload: ContentPayload) -> dict:
    """Overwrite one stage prompt. Free-form markdown, nothing to validate.

    Raises:
        HTTPException: 404 if the name is not an existing mode file -- this
            endpoint edits prompts that already exist, it does not create new
            stages, since a new stage needs code to call it regardless.
    """
    path = _mode_path(name, must_exist=True)
    return _write_text(path, payload.content)


@router.get("/available-models")
def available_models() -> list[str]:
    """The curated model options the settings UI may pick from per stage."""
    return AVAILABLE_MODELS


@router.get("/settings")
def get_pipeline_settings(db: Session = Depends(get_db)) -> dict:
    """Read the live pipeline settings: models per stage, and the tuning knobs.

    The API key and base URL are never included here -- they stay in env
    vars, since this app has no auth and a key does not belong behind an
    endpoint any request can read.
    """
    return _settings_dict(get_or_create_row(db))


@router.put("/settings")
def update_pipeline_settings(payload: SettingsPayload, db: Session = Depends(get_db)) -> dict:
    """Update the pipeline settings. Takes effect on the next batch, no restart.

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
