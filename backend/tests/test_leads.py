"""Tests for POST /leads and GET /admin/leads: the pricing page's lead capture."""

from fastapi.testclient import TestClient

_PAYLOAD = {"name": "Ada Lovelace", "email": "ada@example.com", "plan": "pro"}


def test_create_lead_requires_no_auth(client: TestClient):
    res = client.post("/api/v1/leads", json=_PAYLOAD)
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Ada Lovelace"
    assert body["email"] == "ada@example.com"
    assert body["plan"] == "pro"
    assert body["id"] is not None


def test_admin_can_list_leads(client: TestClient, make_user):
    client.post("/api/v1/leads", json=_PAYLOAD)

    make_user(role="admin")
    res = client.get("/api/v1/admin/leads")
    assert res.status_code == 200
    leads = res.json()
    assert len(leads) == 1
    assert leads[0]["email"] == "ada@example.com"


def test_non_admin_cannot_list_leads(client: TestClient, make_user):
    make_user(role="user")
    res = client.get("/api/v1/admin/leads")
    assert res.status_code == 403
