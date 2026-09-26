"""Bulk cancel must silently skip orders that are not in placed status (R28)."""
from __future__ import annotations


def test_bulk_cancel_skips_non_placed_orders_silently(alice_client):
    # Place an order and deliver it
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]
    alice_client.post(f"/orders/{oid}/deliver")

    # Bulk-cancel the delivered order — must succeed (200) and report it as skipped, not error
    resp = alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})
    assert resp.status_code == 200
    data = resp.json()
    assert oid in data["skipped"]
    assert oid not in data["cancelled"]
    assert data["cancelled_count"] == 0
