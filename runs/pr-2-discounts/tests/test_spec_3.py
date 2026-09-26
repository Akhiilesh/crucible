"""A discount applied to an order by a user who does not own it must return 403."""
from __future__ import annotations


def test_discount_non_owner_returns_403(alice_client, bob_client):
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    resp2 = bob_client.post(f"/orders/{oid}/discount", json={"percent": 10})
    assert resp2.status_code == 403
