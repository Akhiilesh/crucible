"""Stock must not be restored when bulk-cancel skips an order belonging to another user."""
import app.store as store


def test_bulk_cancel_does_not_restore_stock_for_other_users_order(alice_client, bob_client):
    # Record initial stock
    initial_stock = store.products["p1"].stock

    # Bob creates an order consuming some stock
    r = bob_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 3}]})
    assert r.status_code == 201
    oid = r.json()["id"]

    stock_after_order = store.products["p1"].stock
    assert stock_after_order == initial_stock - 3

    # Alice attempts to bulk-cancel Bob's order
    r2 = alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})
    assert r2.status_code == 200

    # Stock must remain reduced (not restored) since Alice does not own this order
    assert store.products["p1"].stock == stock_after_order
