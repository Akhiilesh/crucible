"""A discount percentage of 0 is outside the valid range and must return 400."""
from __future__ import annotations


def test_discount_zero_percent_returns_400(alice_client):
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    resp2 = alice_client.post(f"/orders/{oid}/discount", json={"percent": 0})
    assert resp2.status_code == 400
