"""Loads AsyncApply settings from the DB, overridden by env vars from backend/.env.

The DB row is the live, UI-editable configuration (replacing defaults.yaml, which
needed a rebuild to change anything). Env vars still override it for a one-off
deploy-time tweak, and secrets -- the API key, the base URL -- are env-only,
since there is no auth on this app's API and a key does not belong in a table
any request can read.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from database import SessionLocal
from database import models as db_models

SERVICE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

# The stage models a fresh settings row seeds with, and what a request falls
# back to if the DB row is somehow missing. Cheap-and-capable was chosen for
# extraction, the stronger option for the stage that judges and writes prose.
SEED_DEFAULTS = {
    "model_extract_jd": "deepseek/deepseek-v4-flash",
    "model_evaluate_job": "deepseek/deepseek-v3.2",
    "model_find_contact": "deepseek/deepseek-v3.2",
    "parallelism": 2,
    "max_attempts": 3,
    "stage_timeout": 300,
    "fetch_timeout": 45,
    "cv_max_pages": 1,
    "output_dir": None,
}

# Offered by the Config UI as a per-stage toggle. Kept short and curated
# rather than exposing every OpenRouter model: each one here is verified to
# support tool calls, strict JSON schema and OpenRouter's require_parameters
# routing, which is what the pipeline actually depends on.
AVAILABLE_MODELS = [
    "deepseek/deepseek-v4-flash",
    "deepseek/deepseek-v3.2",
    "qwen/qwen3-30b-a3b",
    "google/gemini-2.5-flash-lite",
    "google/gemini-2.5-flash",
    "openai/gpt-4.1-mini",
]


@dataclass(frozen=True)
class AsyncApplySettings:
    """Resolved configuration for one AsyncApply pipeline run."""

    models: dict[str, str]
    parallelism: int
    max_attempts: int
    stage_timeout: int
    fetch_timeout: int
    cv_max_pages: int
    output_dir: Path
    openrouter_api_key: str | None
    openrouter_base_url: str


def _coerce_int(raw: str, default: int) -> int:
    """Parse an env override into an int, falling back to the DB value.

    Args:
        raw: The raw environment value.
        default: The DB row's value, used when the env value does not parse.

    Returns:
        The parsed int, or default.
    """
    try:
        return int(raw)
    except ValueError:
        return default


def get_or_create_row(db) -> db_models.AsyncApplySettings:
    """Fetch the singleton settings row, seeding it on first use.

    Args:
        db: An active DB session.

    Returns:
        The settings row, id=1.
    """
    row = db.get(db_models.AsyncApplySettings, 1)
    if row is None:
        row = db_models.AsyncApplySettings(id=1, **SEED_DEFAULTS)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_settings() -> AsyncApplySettings:
    """Build the AsyncApply settings from the DB plus environment overrides.

    Uncached: reading one row is negligible next to the LLM calls that follow,
    and it means a Config UI edit takes effect on the very next batch.

    Returns:
        The resolved settings.
    """
    db = SessionLocal()
    try:
        row = get_or_create_row(db)
        stage_defaults = {
            "extract_jd": row.model_extract_jd,
            "evaluate_job": row.model_evaluate_job,
            "find_contact": row.model_find_contact,
        }
    finally:
        db.close()

    global_model = os.environ.get("ASYNCAPPLY_MODEL", "").strip()
    models = {
        stage: os.environ.get(f"ASYNCAPPLY_MODEL_{stage.upper()}", "").strip() or global_model or default
        for stage, default in stage_defaults.items()
    }

    def env_int(key: str, default: int) -> int:
        raw = os.environ.get(f"ASYNCAPPLY_{key.upper()}", "").strip()
        return _coerce_int(raw, default) if raw else default

    output_dir = os.environ.get("ASYNCAPPLY_OUTPUT_DIR", "").strip() or row.output_dir

    return AsyncApplySettings(
        models=models,
        parallelism=env_int("parallelism", row.parallelism),
        max_attempts=env_int("max_attempts", row.max_attempts),
        stage_timeout=env_int("stage_timeout", row.stage_timeout),
        fetch_timeout=env_int("fetch_timeout", row.fetch_timeout),
        cv_max_pages=env_int("cv_max_pages", row.cv_max_pages),
        output_dir=Path(output_dir) if output_dir else SERVICE_DIR / "output",
        openrouter_api_key=os.environ.get("OPENROUTER_API_KEY") or None,
        openrouter_base_url=os.environ.get("OPENROUTER_BASE_URL", "").strip() or DEFAULT_BASE_URL,
    )
