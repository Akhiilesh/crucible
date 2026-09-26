"""Test that a refund request with an unknown X-User-Id returns 401."""
from fastapi.testclient import TestClient
from app.main import app
import app.store as store


def test_refund_unknown_user_returns_401(alice_client):
    # Alice creates and delivers an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]
    alice_client.post(f"/orders/{oid}/deliver")

    # An unknown user tries to refund — must return 401
    unknown = TestClient(app, raise_server_exceptions=False, headers={"x-user-id": "unknown-xyz"})
    resp = unknown.post(f"/orders/{oid}/refund", json={"amount_paise": 100})
    assert resp.status_code == 401
