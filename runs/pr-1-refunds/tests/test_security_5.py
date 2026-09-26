"""Test that Bob cannot trigger a state change on Alice's order via the refund endpoint."""
from fastapi.testclient import TestClient
from app.main import app
import app.store as store


def test_bob_cannot_change_alice_order_state_via_refund(alice_client, bob_client):
    # Alice creates and delivers an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]
    alice_client.post(f"/orders/{oid}/deliver")

    original_status = store.orders[oid].status

    # Bob attempts to refund Alice's order
    bob_client.post(f"/orders/{oid}/refund", json={"amount_paise": 100})

    # Alice's order status must not have changed
    assert store.orders[oid].status == original_status
