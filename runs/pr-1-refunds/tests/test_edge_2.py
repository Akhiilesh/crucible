"""Refund amount exceeding the order total must be rejected with 400."""
from fastapi.testclient import TestClient

import app.store as store


def test_refund_amount_exceeds_total_returns_400(alice_client: TestClient) -> None:
    # Create and deliver an order (p1 price is 10000 paise per unit)
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]
    total = resp.json()["total_paise"]

    deliver_resp = alice_client.post(f"/orders/{oid}/deliver")
    assert deliver_resp.status_code == 200

    # Attempt to refund more than the order total — must be rejected per R18
    refund_resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": total + 1})
    assert refund_resp.status_code == 400
