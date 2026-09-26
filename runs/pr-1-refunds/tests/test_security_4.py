"""Test that a failed refund error body does not leak another user's data."""
from fastapi.testclient import TestClient
from app.main import app
import app.store as store
import json


def test_refund_forbidden_error_does_not_leak_order_data(alice_client, bob_client):
    # Alice creates an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    alice_order = resp.json()
    oid = alice_order["id"]
    alice_client.post(f"/orders/{oid}/deliver")

    # Bob attempts to refund Alice's order — 403 expected
    resp = bob_client.post(f"/orders/{oid}/refund", json={"amount_paise": 100})
    assert resp.status_code == 403

    # The error body must not expose Alice's order contents
    body_text = resp.text
    assert alice_order.get("total_paise") is None or str(alice_order["total_paise"]) not in body_text
    assert alice_order.get("user_id", "") not in body_text or alice_order.get("user_id") == ""
