"""Tests for /asyncapply/config: reading and writing a user's own profile.yml
and agent DNA, plus the admin-only mode prompts and pipeline settings."""

from fastapi.testclient import TestClient


def _write_temp_modes(tmp_path, monkeypatch):
    """Point the config router at a throwaway modes directory, not the real prompts."""
    import routers.asyncapply_config as cfg

    modes_dir = tmp_path / "modes"
    modes_dir.mkdir()
    (modes_dir / "evaluate_job.md").write_text("Original prompt.")

    monkeypatch.setattr(cfg, "MODES_DIR", modes_dir)
    return modes_dir


_PROFILE_PAYLOAD = {
    "candidate": {"full_name": "Ada Lovelace"},
    "location": {"authorized_in": ["GB"]},
    "target_roles": ["Backend Engineer"],
    "cv": {"technologies": ["Python"]},
}


def test_profile_round_trips(client: TestClient, make_user):
    make_user()

    put = client.put("/api/v1/asyncapply/config/profile", json=_PROFILE_PAYLOAD)
    assert put.status_code == 200

    got = client.get("/api/v1/asyncapply/config/profile").json()
    assert got["candidate"]["full_name"] == "Ada Lovelace"


def test_a_new_user_gets_an_empty_but_valid_profile_shell(client: TestClient, make_user):
    make_user()
    got = client.get("/api/v1/asyncapply/config/profile")
    assert got.status_code == 200
    assert got.json()["candidate"]["full_name"] == ""


def test_a_profile_is_private_to_its_own_user(client: TestClient, make_user):
    make_user()
    client.put("/api/v1/asyncapply/config/profile", json=_PROFILE_PAYLOAD)

    make_user()  # switch identity
    got = client.get("/api/v1/asyncapply/config/profile").json()
    assert got["candidate"]["full_name"] == ""


def test_a_malformed_profile_is_rejected(client: TestClient, make_user):
    make_user()
    bad = client.put("/api/v1/asyncapply/config/profile", json={"candidate": "not a mapping"})
    assert bad.status_code == 422


def test_filling_profile_from_a_cv_returns_the_extraction_without_saving(
    client: TestClient, make_user, monkeypatch
):
    import routers.asyncapply_config as cfg
    from services.asyncapply.profile_schema import ExtractedProfile

    async def fake_extract(pdf_bytes: bytes) -> ExtractedProfile:
        return ExtractedProfile(full_name="Ada Lovelace", technologies=["Python"])

    monkeypatch.setattr(cfg, "extract_profile_from_cv", fake_extract)
    make_user()

    res = client.post(
        "/api/v1/asyncapply/config/profile/from-cv",
        files={"file": ("cv.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert res.status_code == 200
    assert res.json()["full_name"] == "Ada Lovelace"

    # Nothing was saved -- the extraction is only ever returned for the
    # frontend to merge into the form and let the user review it.
    assert client.get("/api/v1/asyncapply/config/profile").json()["candidate"]["full_name"] == ""


def test_a_bad_cv_upload_is_a_422_not_a_500(client: TestClient, make_user, monkeypatch):
    import routers.asyncapply_config as cfg

    async def boom(pdf_bytes: bytes):
        raise ValueError("not a real PDF")

    monkeypatch.setattr(cfg, "extract_profile_from_cv", boom)
    make_user()

    res = client.post(
        "/api/v1/asyncapply/config/profile/from-cv",
        files={"file": ("cv.pdf", b"garbage", "application/pdf")},
    )
    assert res.status_code == 422


def test_agent_dna_round_trips(client: TestClient, make_user):
    make_user()
    client.put("/api/v1/asyncapply/config/agent-dna", json={"content": "No em dashes."})
    got = client.get("/api/v1/asyncapply/config/agent-dna")
    assert got.json()["content"] == "No em dashes."


def test_modes_are_listed_and_editable_by_an_admin(client: TestClient, make_user, tmp_path, monkeypatch):
    _write_temp_modes(tmp_path, monkeypatch)
    make_user(role="admin")

    names = client.get("/api/v1/asyncapply/config/modes").json()
    assert names == ["evaluate_job"]

    got = client.get("/api/v1/asyncapply/config/modes/evaluate_job")
    assert got.json()["content"] == "Original prompt."

    client.put("/api/v1/asyncapply/config/modes/evaluate_job", json={"content": "New prompt."})
    assert client.get("/api/v1/asyncapply/config/modes/evaluate_job").json()["content"] == "New prompt."


def test_modes_are_forbidden_to_a_regular_user(client: TestClient, make_user, tmp_path, monkeypatch):
    _write_temp_modes(tmp_path, monkeypatch)
    make_user()
    assert client.get("/api/v1/asyncapply/config/modes").status_code == 403


def test_a_mode_that_does_not_exist_is_not_creatable(client: TestClient, make_user, tmp_path, monkeypatch):
    """Editing an existing prompt is supported; inventing a new stage is not --
    a new stage needs code to call it regardless of what file exists."""
    _write_temp_modes(tmp_path, monkeypatch)
    make_user(role="admin")
    res = client.put("/api/v1/asyncapply/config/modes/made_up_stage", json={"content": "x"})
    assert res.status_code == 404


def test_a_path_traversal_attempt_is_rejected(client: TestClient, make_user, tmp_path, monkeypatch):
    _write_temp_modes(tmp_path, monkeypatch)
    make_user(role="admin")
    res = client.get("/api/v1/asyncapply/config/modes/..%2F..%2Fetc%2Fpasswd")
    assert res.status_code == 404


def test_settings_round_trip(client: TestClient, make_user) -> None:
    make_user(role="admin")
    got = client.get("/api/v1/asyncapply/config/settings").json()
    assert got["model_evaluate_job"]  # seeded on first read

    got["parallelism"] = 5
    got["model_evaluate_job"] = "openai/gpt-4.1-mini"
    put = client.put("/api/v1/asyncapply/config/settings", json=got)
    assert put.status_code == 200
    assert put.json()["parallelism"] == 5

    again = client.get("/api/v1/asyncapply/config/settings").json()
    assert again["model_evaluate_job"] == "openai/gpt-4.1-mini"


def test_settings_are_forbidden_to_a_regular_user(client: TestClient, make_user) -> None:
    make_user()
    assert client.get("/api/v1/asyncapply/config/settings").status_code == 403


def test_an_uncurated_model_is_rejected(client: TestClient, make_user) -> None:
    make_user(role="admin")
    current = client.get("/api/v1/asyncapply/config/settings").json()
    current["model_evaluate_job"] = "some-random/model-nobody-vetted"
    res = client.put("/api/v1/asyncapply/config/settings", json=current)
    assert res.status_code == 422


def test_available_models_lists_the_curated_options(client: TestClient, make_user) -> None:
    make_user()
    models = client.get("/api/v1/asyncapply/config/available-models").json()
    assert "deepseek/deepseek-v3.2" in models
