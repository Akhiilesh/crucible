"""A user must not be able to bulk-cancel orders belonging to another user."""
from __future__ import annotations

import app.store as store


def test_bulk_cancel_cannot_cancel_another_users_order(alice_client, bob_client):
    # Alice places an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    # Bob attempts to bulk-cancel Alice's order
    resp = bob_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})
    # The order must NOT be cancelled — a 403 or the order must remain in the skipped list
    # with the order still in placed status
    order = store.orders.get(oid)
    assert order is not None
    assert order.status.value == "placed", (
        "Another user's order must not be cancelled via bulk-cancel"
    )
