"""Refund request with a negative amount must be rejected with 400."""
from fastapi.testclient import TestClient

import app.store as store


def test_refund_negative_amount_returns_400(alice_client: TestClient) -> None:
    # Create and deliver an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    deliver_resp = alice_client.post(f"/orders/{oid}/deliver")
    assert deliver_resp.status_code == 200

    # Attempt to refund with a negative amount — must be rejected per R18
    refund_resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": -1})
    assert refund_resp.status_code == 400
