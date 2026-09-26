"""Refund amount of 0 must be rejected with 400."""
import pytest
from fastapi.testclient import TestClient

import app.store as store


def test_refund_amount_zero_returns_400(alice_client: TestClient) -> None:
    # Create and deliver an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    deliver_resp = alice_client.post(f"/orders/{oid}/deliver")
    assert deliver_resp.status_code == 200

    # Attempt to refund with amount 0 — must be rejected per R18
    refund_resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 0})
    assert refund_resp.status_code == 400
