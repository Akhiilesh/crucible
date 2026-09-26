"""Bulk cancel must restore stock only for orders actually cancelled by the request (R27)."""
from __future__ import annotations

import app.store as store


def test_bulk_cancel_does_not_restore_stock_for_skipped_orders(alice_client):
    # Place two orders
    resp1 = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 2}]})
    assert resp1.status_code == 201
    oid_placed = resp1.json()["id"]

    resp2 = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 3}]})
    assert resp2.status_code == 201
    oid_delivered = resp2.json()["id"]

    # Deliver the second order so it is not eligible for cancellation
    alice_client.post(f"/orders/{oid_delivered}/deliver")

    stock_before_bulk = store.products["p1"].stock

    # Bulk-cancel both; only the placed one should be cancelled
    alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid_placed, oid_delivered]})

    # Stock should be restored only for oid_placed (qty=2); oid_delivered (qty=3) must NOT be restored
    assert store.products["p1"].stock == stock_before_bulk + 2
