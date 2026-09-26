"""Bulk-cancel must not cancel orders owned by another user."""
import app.store as store


def test_bulk_cancel_does_not_cancel_other_users_order(alice_client, bob_client):
    # Bob creates an order
    r = bob_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 2}]})
    assert r.status_code == 201
    oid = r.json()["id"]

    # Alice attempts to bulk-cancel Bob's order
    r2 = alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})
    assert r2.status_code == 200

    # Bob's order must still be in placed status
    r3 = bob_client.get(f"/orders/{oid}")
    assert r3.status_code == 200
    assert r3.json()["status"] == "placed"
