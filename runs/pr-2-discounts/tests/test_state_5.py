"""Discounting two different orders independently must not affect each other's totals."""
from __future__ import annotations


def test_discount_state_is_independent_per_order(alice_client):
    # Create two separate orders
    r1 = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 4}]})
    assert r1.status_code == 201
    oid1 = r1.json()["id"]
    total1 = r1.json()["total_paise"]

    r2 = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 2}]})
    assert r2.status_code == 201
    oid2 = r2.json()["id"]
    total2 = r2.json()["total_paise"]

    # Apply 50% discount to order 1 only
    rd = alice_client.post(f"/orders/{oid1}/discount", json={"percent": 50})
    assert rd.status_code == 200

    # Order 2 must be completely unaffected
    rget2 = alice_client.get(f"/orders/{oid2}")
    assert rget2.status_code == 200
    assert rget2.json()["total_paise"] == total2
    assert rget2.json()["discount_percent"] is None
