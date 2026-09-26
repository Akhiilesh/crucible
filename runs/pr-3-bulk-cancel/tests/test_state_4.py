"""Delivered orders must be silently skipped by bulk-cancel and their stock must not be restored."""
import app.store as store


def test_bulk_cancel_skips_delivered_order_no_stock_change(alice_client):
    initial_stock = store.products["p2"].stock

    # Alice creates an order
    r = alice_client.post("/orders", json={"items": [{"product_id": "p2", "qty": 2}]})
    assert r.status_code == 201
    oid = r.json()["id"]

    # Deliver the order
    r2 = alice_client.post(f"/orders/{oid}/deliver")
    assert r2.status_code == 200
    assert r2.json()["status"] == "delivered"

    stock_after_order = store.products["p2"].stock

    # Bulk-cancel includes the delivered order — it must be skipped
    r3 = alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})
    assert r3.status_code == 200
    data = r3.json()
    assert oid not in data["cancelled"]
    assert oid in data["skipped"]

    # Stock must not have been restored for the delivered (skipped) order
    assert store.products["p2"].stock == stock_after_order
