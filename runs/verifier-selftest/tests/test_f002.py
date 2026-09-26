"""F-002 — Fake: wrong expectation + ungrounded basis (R99 does not exist).

Asserts a placed order can be refunded (should return 400, not 200).
Basis cites spec/orders.md#R99 which is not a real rule — G4 rejects this
before any test is run.
"""
from __future__ import annotations


def test_refund_placed_order_succeeds(alice_client):
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    oid = resp.json()["id"]
    # Wrong: spec requires delivered status; this asserts the wrong behaviour
    resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 500})
    assert resp.status_code == 200
