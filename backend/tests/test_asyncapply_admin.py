"""Tests for /asyncapply/admin: usage summaries, drill-down detail, workspace
stats, and the admin-only gate on all of it."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from database import get_db, models
from main import app


def _seed_batch(user_id: int, *, created_at: datetime, items: list[tuple[str, float | None]]) -> None:
    """Create a batch with items directly in the test DB, bypassing the
    real pipeline -- these tests care about aggregation, not processing."""
    db = next(app.dependency_overrides[get_db]())
    batch = models.AsyncApplyBatch(user_id=user_id, state="done", created_at=created_at)
    db.add(batch)
    db.flush()
    for state, cost in items:
        db.add(
            models.AsyncApplyItem(
                batch_id=batch.id, raw_input="x", state=state, cost_usd=cost, created_at=created_at
            )
        )
    db.commit()


def test_users_are_forbidden_to_a_regular_user(client: TestClient, make_user) -> None:
    make_user()
    assert client.get("/api/v1/asyncapply/admin/users").status_code == 403
    assert client.get("/api/v1/asyncapply/admin/stats").status_code == 403
    assert client.get("/api/v1/asyncapply/admin/users/1/detail").status_code == 403


def test_user_list_includes_usage_summary(client: TestClient, make_user) -> None:
    user = make_user()
    _seed_batch(user.id, created_at=datetime.utcnow(), items=[("done", 0.02), ("done", 0.03)])

    make_user(role="admin")
    rows = client.get("/api/v1/asyncapply/admin/users").json()
    row = next(r for r in rows if r["id"] == user.id)

    assert row["batch_count"] == 1
    assert row["item_count"] == 2
    assert row["last_active_at"] is not None


def test_a_user_with_no_activity_has_zeroed_usage(client: TestClient, make_user) -> None:
    make_user()
    make_user(role="admin")
    rows = client.get("/api/v1/asyncapply/admin/users").json()
    assert all(r["batch_count"] >= 0 for r in rows)
    fresh = rows[0]
    assert fresh["batch_count"] == 0
    assert fresh["item_count"] == 0
    assert fresh["last_active_at"] is None


def test_user_detail_lists_their_batches(client: TestClient, make_user) -> None:
    user = make_user()
    _seed_batch(user.id, created_at=datetime.utcnow(), items=[("done", 0.05)])

    make_user(role="admin")
    detail = client.get(f"/api/v1/asyncapply/admin/users/{user.id}/detail").json()

    assert detail["email"] == user.email
    assert len(detail["batches"]) == 1
    assert detail["batches"][0]["item_count"] == 1
    assert detail["batches"][0]["cost_usd"] == 0.05


def test_user_detail_404s_for_an_unknown_user(client: TestClient, make_user) -> None:
    make_user(role="admin")
    assert client.get("/api/v1/asyncapply/admin/users/99999/detail").status_code == 404


def test_stats_aggregate_within_the_window(client: TestClient, make_user) -> None:
    user = make_user()
    _seed_batch(
        user.id,
        created_at=datetime.utcnow(),
        items=[("done", 0.10), ("failed", None)],
    )
    _seed_batch(
        user.id,
        created_at=datetime.utcnow() - timedelta(days=60),
        items=[("done", 5.00)],
    )

    make_user(role="admin")
    recent = client.get("/api/v1/asyncapply/admin/stats?window=30d").json()
    everything = client.get("/api/v1/asyncapply/admin/stats?window=all").json()

    assert recent["total_batches"] == 1
    assert recent["total_items"] == 2
    assert recent["total_spend_usd"] == 0.10
    assert recent["items_done"] == 1
    assert recent["items_failed"] == 1

    assert everything["total_batches"] == 2
    assert everything["total_items"] == 3
    assert round(everything["total_spend_usd"], 2) == 5.10


def test_an_invalid_window_is_rejected(client: TestClient, make_user) -> None:
    make_user(role="admin")
    res = client.get("/api/v1/asyncapply/admin/stats?window=nonsense")
    assert res.status_code == 422


def test_budget_response_still_carries_usage_fields(client: TestClient, make_user) -> None:
    user = make_user()
    make_user(role="admin")
    res = client.patch(f"/api/v1/asyncapply/admin/users/{user.id}/budget", json={"token_budget_usd": 10.0})
    assert res.status_code == 200
    body = res.json()
    assert body["token_budget_usd"] == 10.0
    assert body["batch_count"] == 0
