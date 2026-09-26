"""The order total after applying a discount must never be negative."""
from __future__ import annotations


def test_discount_total_never_negative(alice_client):
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    resp2 = alice_client.post(f"/orders/{oid}/discount", json={"percent": 50})
    assert resp2.status_code == 200
    assert resp2.json()["total_paise"] >= 0
