"""Test that a user cannot refund an order belonging to another user."""
import pytest
from fastapi.testclient import TestClient

import app.store as store


def test_refund_another_users_order_returns_403(alice_client, bob_client):
    # Alice creates and delivers an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    alice_client.post(f"/orders/{oid}/deliver")

    # Bob attempts to refund Alice's order — must be 403
    resp = bob_client.post(f"/orders/{oid}/refund", json={"amount_paise": 100})
    assert resp.status_code == 403
