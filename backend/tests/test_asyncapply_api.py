"""Tests for the /asyncapply batch endpoints, with the background pipeline worker stubbed out."""

import pytest
from fastapi.testclient import TestClient

from routers import asyncapply


@pytest.fixture(autouse=True)
def stub_process_batch(monkeypatch: pytest.MonkeyPatch):
    """Prevent the real Agent SDK pipeline from running during API tests."""
    calls = []

    async def fake_process_batch(batch_id: int) -> None:
        calls.append(batch_id)

    monkeypatch.setattr(asyncapply, "process_batch", fake_process_batch)
    return calls


def test_create_batch_returns_queued_items(client: TestClient) -> None:
    response = client.post("/api/v1/asyncapply/batches", json={"items": ["https://a.com/job", "pasted JD text"]})

    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "queued"
    assert len(body["items"]) == 2
    assert {item["state"] for item in body["items"]} == {"queued"}


def test_create_batch_rejects_empty_items(client: TestClient) -> None:
    response = client.post("/api/v1/asyncapply/batches", json={"items": []})
    assert response.status_code == 422


def test_get_batch_returns_404_for_unknown_id(client: TestClient) -> None:
    response = client.get("/api/v1/asyncapply/batches/999")
    assert response.status_code == 404


def test_get_batch_round_trips_created_batch(client: TestClient) -> None:
    created = client.post("/api/v1/asyncapply/batches", json={"items": ["https://a.com/job"]}).json()

    response = client.get(f"/api/v1/asyncapply/batches/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_list_batches_includes_created_batch(client: TestClient) -> None:
    created = client.post("/api/v1/asyncapply/batches", json={"items": ["https://a.com/job"]}).json()

    response = client.get("/api/v1/asyncapply/batches")

    assert response.status_code == 200
    assert any(batch["id"] == created["id"] for batch in response.json())


def test_retry_batch_requeues_failed_items_only(client: TestClient) -> None:
    created = client.post("/api/v1/asyncapply/batches", json={"items": ["https://a.com/job"]}).json()

    response = client.post(f"/api/v1/asyncapply/batches/{created['id']}/retry")

    assert response.status_code == 200
    assert response.json()["state"] == "queued"


def test_download_cv_returns_the_pdf(client: TestClient, tmp_path) -> None:
    pdf = tmp_path / "1-acme-cv.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    created = client.post("/api/v1/asyncapply/batches", json={"items": ["https://a.com/job"]}).json()
    item_id = created["items"][0]["id"]
    client.patch(f"/api/v1/asyncapply/items/{item_id}", json={"status": "applied"})

    # Reach the same in-memory session the app is using, not the real DB.
    from database import get_db, models
    from main import app

    db = next(app.dependency_overrides[get_db]())
    db.get(models.AsyncApplyItem, item_id).cv_pdf_path = str(pdf)
    db.commit()

    response = client.get(f"/api/v1/asyncapply/items/{item_id}/cv")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_download_unknown_asset_is_404(client: TestClient) -> None:
    created = client.post("/api/v1/asyncapply/batches", json={"items": ["https://a.com/job"]}).json()
    item_id = created["items"][0]["id"]

    assert client.get(f"/api/v1/asyncapply/items/{item_id}/passport").status_code == 404


def test_download_is_404_when_no_asset_was_generated(client: TestClient) -> None:
    created = client.post("/api/v1/asyncapply/batches", json={"items": ["https://a.com/job"]}).json()
    item_id = created["items"][0]["id"]

    response = client.get(f"/api/v1/asyncapply/items/{item_id}/cv")

    assert response.status_code == 404
    assert "no cv was generated" in response.json()["detail"]


def test_update_item_status(client: TestClient) -> None:
    created = client.post("/api/v1/asyncapply/batches", json={"items": ["https://a.com/job"]}).json()
    item_id = created["items"][0]["id"]

    response = client.patch(f"/api/v1/asyncapply/items/{item_id}", json={"status": "applied"})

    assert response.status_code == 200
    assert response.json()["status"] == "applied"


def test_list_items_filters_by_status(client: TestClient) -> None:
    created = client.post(
        "/api/v1/asyncapply/batches", json={"items": ["https://a.com/1", "https://a.com/2"]}
    ).json()
    client.patch(f"/api/v1/asyncapply/items/{created['items'][0]['id']}", json={"status": "applied"})

    assert len(client.get("/api/v1/asyncapply/items").json()) == 2
    applied = client.get("/api/v1/asyncapply/items?status=applied").json()
    assert len(applied) == 1
    assert applied[0]["status"] == "applied"


def test_a_logo_uploads_and_serves_back(client: TestClient, tmp_path, monkeypatch) -> None:
    from services.asyncapply.settings import loader

    monkeypatch.setattr(
        loader,
        "get_settings",
        lambda: loader.AsyncApplySettings(
            models={}, parallelism=1, max_attempts=1, stage_timeout=1, fetch_timeout=1,
            cv_max_pages=1, output_dir=tmp_path, openrouter_api_key=None,
            openrouter_base_url="",
        ),
    )
    monkeypatch.setattr(asyncapply, "get_settings", loader.get_settings)

    png_bytes = b"\x89PNG\r\n\x1a\nfake"
    put = client.put(
        "/api/v1/asyncapply/companies/Acme%20Inc/logo",
        files={"file": ("logo.png", png_bytes, "image/png")},
    )
    assert put.status_code == 200

    got = client.get("/api/v1/asyncapply/companies/Acme%20Inc/logo")
    assert got.status_code == 200
    assert got.content == png_bytes


def test_a_company_with_no_logo_is_404(client: TestClient) -> None:
    res = client.get("/api/v1/asyncapply/companies/NobodyUploadedThis/logo")
    assert res.status_code == 404


def test_download_filename_is_hr_facing_not_the_storage_path(
    client: TestClient, tmp_path, monkeypatch
) -> None:
    """Two applications for the same role must not collide on disk, but the
    name offered to the browser should still read like a real application."""
    import routers.asyncapply as asyncapply_router
    from database import get_db, models
    from main import app
    from services.asyncapply.context.loader import AsyncApplyContext

    profile = {"candidate": {"full_name": "Javier Dominguez Segura"}}
    monkeypatch.setattr(
        asyncapply_router,
        "load_context",
        lambda: AsyncApplyContext(profile=profile, voice_dna=""),
    )

    pdf = tmp_path / "internal-storage-name.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    created = client.post("/api/v1/asyncapply/batches", json={"items": ["https://a.com/job"]}).json()
    item_id = created["items"][0]["id"]

    db = next(app.dependency_overrides[get_db]())
    item = db.get(models.AsyncApplyItem, item_id)
    item.cv_pdf_path = str(pdf)
    item.role = "Software Engineer II"
    db.commit()

    response = client.get(f"/api/v1/asyncapply/items/{item_id}/cv")

    assert response.status_code == 200
    assert 'filename="Javier_D_SoftwareEngineerII_CV.pdf"' in response.headers["content-disposition"]


def test_delete_item_removes_the_row_and_its_pdfs(client: TestClient, tmp_path) -> None:
    from database import get_db, models
    from main import app

    cv = tmp_path / "cv.pdf"
    cover = tmp_path / "cover.pdf"
    cv.write_bytes(b"%PDF cv")
    cover.write_bytes(b"%PDF cover")

    created = client.post("/api/v1/asyncapply/batches", json={"items": ["https://a.com/job"]}).json()
    item_id = created["items"][0]["id"]

    db = next(app.dependency_overrides[get_db]())
    item = db.get(models.AsyncApplyItem, item_id)
    item.cv_pdf_path = str(cv)
    item.cover_letter_pdf_path = str(cover)
    db.commit()

    assert client.delete(f"/api/v1/asyncapply/items/{item_id}").status_code == 204
    assert client.get(f"/api/v1/asyncapply/items/{item_id}/cv").status_code == 404
    assert not cv.exists()
    assert not cover.exists()


def test_deleting_an_item_with_no_pdfs_still_works(client: TestClient) -> None:
    """A hard-stopped item never generated assets; deleting it must not 500."""
    created = client.post("/api/v1/asyncapply/batches", json={"items": ["https://a.com/job"]}).json()
    item_id = created["items"][0]["id"]

    assert client.delete(f"/api/v1/asyncapply/items/{item_id}").status_code == 204


def test_deleting_a_missing_item_is_404(client: TestClient) -> None:
    assert client.delete("/api/v1/asyncapply/items/99999").status_code == 404
