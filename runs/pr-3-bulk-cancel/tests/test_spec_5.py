"""Bulk cancel must cancel each eligible placed order and restore its stock (R25, R13)."""
from __future__ import annotations

import app.store as store


def test_bulk_cancel_cancels_placed_orders_and_restores_stock(alice_client):
    stock_before = store.products["p1"].stock

    # Place two orders
    resp1 = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 2}]})
    assert resp1.status_code == 201
    oid1 = resp1.json()["id"]

    resp2 = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 3}]})
    assert resp2.status_code == 201
    oid2 = resp2.json()["id"]

    # Bulk-cancel both
    resp = alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid1, oid2]})
    assert resp.status_code == 200
    data = resp.json()

    # Both should be in cancelled list with correct count
    assert oid1 in data["cancelled"]
    assert oid2 in data["cancelled"]
    assert data["cancelled_count"] == 2

    # Stock must be fully restored
    assert store.products["p1"].stock == stock_before
