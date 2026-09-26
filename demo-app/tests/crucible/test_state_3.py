"""Applying a discount to a cancelled order must be rejected with 400."""
from __future__ import annotations


def test_discount_on_cancelled_order_returns_400(alice_client):
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    # Cancel the order
    r_cancel = alice_client.post(f"/orders/{oid}/cancel")
    assert r_cancel.status_code == 200
    assert r_cancel.json()["status"] == "cancelled"

    # Attempting to discount a cancelled order must be rejected
    r_discount = alice_client.post(f"/orders/{oid}/discount", json={"percent": 10})
    assert r_discount.status_code == 400
