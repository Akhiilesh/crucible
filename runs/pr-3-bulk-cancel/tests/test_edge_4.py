"""Bulk-cancelling another user's placed order must not restore that order's stock."""
from __future__ import annotations

import app.store as store


def test_bulk_cancel_does_not_restore_stock_for_another_users_order(alice_client, bob_client):
    # Record stock before Alice's order
    stock_before = store.products["p1"].stock

    # Alice places an order consuming stock
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 5}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    stock_after_order = store.products["p1"].stock
    assert stock_after_order == stock_before - 5

    # Bob attempts to bulk-cancel Alice's order
    bob_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})

    # Stock must remain at the reduced level — Bob cannot restore Alice's stock
    assert store.products["p1"].stock == stock_after_order, (
        "Stock must not be restored when an unauthorized user attempts bulk-cancel"
    )
