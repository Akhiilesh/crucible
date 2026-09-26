"""F-001 — Real bug: refund window uses created_at instead of delivered_at (R16).

On pr-1-refunds the window is counted from created_at. This test proves the
bug by backdating created_at to 20 days ago while keeping delivered_at only
2 days ago — a refund should succeed per the spec (within 14 days of delivery)
but the buggy code rejects it because 20 days have passed since creation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import app.store as store


def test_refund_window_uses_created_at(alice_client):
    # Place and deliver an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    alice_client.post(f"/orders/{oid}/deliver")

    # Backdate created_at to 20 days ago, delivered_at to 2 days ago
    now = datetime.now(tz=timezone.utc)
    store.orders[oid] = store.orders[oid].model_copy(update={
        "created_at": now - timedelta(days=20),
        "delivered_at": now - timedelta(days=2),
    })

    # Spec R16: window is 14 days from delivered_at (2 days ago) → should be 200
    resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 500})
    assert resp.status_code == 200
