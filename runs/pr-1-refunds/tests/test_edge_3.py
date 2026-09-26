"""Refund request exactly at the 14-day boundary from delivered_at must succeed."""
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

import app.store as store


def test_refund_exactly_at_14_day_window_boundary_succeeds(alice_client: TestClient) -> None:
    # Create and deliver an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    deliver_resp = alice_client.post(f"/orders/{oid}/deliver")
    assert deliver_resp.status_code == 200

    # Backdate delivered_at to exactly 14 days ago (within the window boundary)
    exactly_14d_ago = datetime.now(timezone.utc) - timedelta(days=14) + timedelta(seconds=10)
    store.orders[oid] = store.orders[oid].model_copy(update={"delivered_at": exactly_14d_ago})

    # A refund request within the 14-day window from delivered_at must succeed per R16/R17
    total = store.orders[oid].total_paise
    refund_resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": total})
    assert refund_resp.status_code == 200
