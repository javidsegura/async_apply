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


def test_profile_round_trips(client: TestClient, make_user):
    make_user()

    put = client.put("/api/v1/asyncapply/config/profile", json={"content": "candidate:\n  name: Ada\n"})
    assert put.status_code == 200

    got = client.get("/api/v1/asyncapply/config/profile")
    assert "Ada" in got.json()["content"]


def test_a_profile_is_private_to_its_own_user(client: TestClient, make_user):
    make_user()
    client.put("/api/v1/asyncapply/config/profile", json={"content": "candidate:\n  name: Ada\n"})

    make_user()  # switch identity
    got = client.get("/api/v1/asyncapply/config/profile")
    assert got.json()["content"] == ""


def test_invalid_yaml_is_rejected(client: TestClient, make_user):
    make_user()
    client.put("/api/v1/asyncapply/config/profile", json={"content": "candidate:\n  name: Ada\n"})

    bad = client.put("/api/v1/asyncapply/config/profile", json={"content": "candidate: [unterminated"})
    assert bad.status_code == 422

    # The bad write must not have touched what was already stored.
    got = client.get("/api/v1/asyncapply/config/profile")
    assert "Ada" in got.json()["content"]


def test_a_non_mapping_profile_is_rejected(client: TestClient, make_user):
    make_user()
    bad = client.put("/api/v1/asyncapply/config/profile", json={"content": "- just\n- a\n- list\n"})
    assert bad.status_code == 422


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
