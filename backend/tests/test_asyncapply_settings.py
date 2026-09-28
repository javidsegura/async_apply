"""Tests for AsyncApply settings resolution: the DB row plus env overrides."""

import pytest

from services.asyncapply.settings import loader
from services.asyncapply.settings.loader import get_settings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch):
    """The isolated DB comes from conftest's autouse fixture; this just
    clears env vars these tests would otherwise inherit from a real .env."""
    for key in ("ASYNCAPPLY_MODEL", "ASYNCAPPLY_MODEL_EVALUATE_JOB", "ASYNCAPPLY_PARALLELISM",
                "ASYNCAPPLY_OUTPUT_DIR", "OPENROUTER_BASE_URL"):
        monkeypatch.delenv(key, raising=False)


def test_a_fresh_row_is_seeded_with_the_defaults() -> None:
    settings = get_settings()
    assert settings.models["evaluate_job"] == "deepseek/deepseek-v3.2"
    assert settings.parallelism == 2


def test_editing_the_row_changes_the_very_next_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """No restart needed: the point of moving this off defaults.yaml."""
    db = loader.SessionLocal()
    row = loader.get_or_create_row(db)
    row.model_evaluate_job = "openai/gpt-4.1-mini"
    row.parallelism = 5
    db.commit()
    db.close()

    settings = get_settings()
    assert settings.models["evaluate_job"] == "openai/gpt-4.1-mini"
    assert settings.parallelism == 5


def test_a_stage_model_can_be_overridden_by_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASYNCAPPLY_MODEL_EVALUATE_JOB", "moonshotai/kimi-k2")
    assert get_settings().models["evaluate_job"] == "moonshotai/kimi-k2"


def test_the_global_model_override_wins_over_the_db_row(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASYNCAPPLY_MODEL", "global/override")
    assert get_settings().models["extract_jd"] == "global/override"


def test_scalar_settings_coerce_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASYNCAPPLY_PARALLELISM", "8")
    assert get_settings().parallelism == 8


def test_an_unparseable_env_value_falls_back_to_the_db_row(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASYNCAPPLY_PARALLELISM", "not-a-number")
    assert get_settings().parallelism == 2


def test_base_url_defaults_to_openrouter(monkeypatch: pytest.MonkeyPatch) -> None:
    assert get_settings().openrouter_base_url == "https://openrouter.ai/api/v1"

    monkeypatch.setenv("OPENROUTER_BASE_URL", "http://localhost:1234/v1")
    assert get_settings().openrouter_base_url == "http://localhost:1234/v1"


def test_the_api_key_is_never_a_db_column() -> None:
    """A secret has no business living in a table any request can read."""
    row_fields = loader.db_models.AsyncApplySettings.__table__.columns.keys()
    assert "openrouter_api_key" not in row_fields
    assert "openrouter_base_url" not in row_fields
