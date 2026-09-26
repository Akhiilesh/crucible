"""Calling bulk-cancel twice with the same order IDs must not restore stock twice."""
import app.store as store


def test_bulk_cancel_idempotent_stock_restore(alice_client):
    initial_stock = store.products["p1"].stock

    # Alice creates an order
    r = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 4}]})
    assert r.status_code == 201
    oid = r.json()["id"]

    # First bulk-cancel — should cancel and restore stock
    r2 = alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})
    assert r2.status_code == 200
    assert store.products["p1"].stock == initial_stock

    # Second bulk-cancel with the same ID — order is already cancelled, must not restore again
    r3 = alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})
    assert r3.status_code == 200
    # Stock must not exceed initial (no double restore)
    assert store.products["p1"].stock == initial_stock
