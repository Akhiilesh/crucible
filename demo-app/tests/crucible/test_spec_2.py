"""Bulk cancel must not cancel an order owned by a different user (R7, R8)."""
from __future__ import annotations

import app.store as store


def test_bulk_cancel_cannot_cancel_other_users_order(alice_client, bob_client):
    # Alice places an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    alice_order_id = resp.json()["id"]

    # Bob attempts to bulk-cancel Alice's order
    bob_client.post("/orders/bulk-cancel", json={"order_ids": [alice_order_id]})

    # Alice's order must still be in 'placed' status — Bob must not have cancelled it
    assert store.orders[alice_order_id].status == "placed"
