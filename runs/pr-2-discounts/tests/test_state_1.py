"""Applying a discount to the same order twice must not apply the effect twice."""
from __future__ import annotations


def test_discount_cannot_be_applied_twice(alice_client):
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 4}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]
    original_total = resp.json()["total_paise"]

    # First discount: 10% off
    r1 = alice_client.post(f"/orders/{oid}/discount", json={"percent": 10})
    assert r1.status_code == 200
    after_first = r1.json()["total_paise"]
    expected_after_first = original_total - (original_total * 10 // 100)
    assert after_first == expected_after_first

    # Second discount: must be rejected (or be a no-op) — must not compound
    r2 = alice_client.post(f"/orders/{oid}/discount", json={"percent": 10})
    # Either the second call is rejected or the total remains the same as after the first
    assert r2.status_code != 200 or r2.json()["total_paise"] == after_first
