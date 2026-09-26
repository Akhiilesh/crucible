"""Bulk-cancel must only cancel and restore stock for orders owned by the requesting user."""
import app.store as store


def test_bulk_cancel_mixed_owners_only_affects_own_orders(alice_client, bob_client):
    initial_p1 = store.products["p1"].stock
    initial_p2 = store.products["p2"].stock

    # Alice creates an order on p1
    r1 = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 5}]})
    assert r1.status_code == 201
    alice_oid = r1.json()["id"]

    # Bob creates an order on p2
    r2 = bob_client.post("/orders", json={"items": [{"product_id": "p2", "qty": 3}]})
    assert r2.status_code == 201
    bob_oid = r2.json()["id"]

    # Alice bulk-cancels both her own and Bob's order
    r3 = alice_client.post("/orders/bulk-cancel", json={"order_ids": [alice_oid, bob_oid]})
    assert r3.status_code == 200

    # Only Alice's order should be cancelled
    r4 = alice_client.get(f"/orders/{alice_oid}")
    assert r4.status_code == 200
    assert r4.json()["status"] == "cancelled"

    # Bob's order must remain placed
    r5 = bob_client.get(f"/orders/{bob_oid}")
    assert r5.status_code == 200
    assert r5.json()["status"] == "placed"

    # p1 stock restored (Alice's order cancelled), p2 stock NOT restored (Bob's order not cancelled)
    assert store.products["p1"].stock == initial_p1
    assert store.products["p2"].stock == initial_p2 - 3
