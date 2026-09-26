"""A discount percentage of 1 is the minimum valid value and must be accepted (return 200)."""
from __future__ import annotations


def test_discount_1_percent_is_accepted(alice_client):
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    resp2 = alice_client.post(f"/orders/{oid}/discount", json={"percent": 1})
    assert resp2.status_code == 200
