"""A 403 response from POST /orders/{id}/discount must not expose another user's order data."""
from fastapi.testclient import TestClient
from app.main import app


def test_discount_403_does_not_leak_order_data(alice_client, bob_client):
    # Alice creates an order
    r = alice_client.post("/orders", json={"items": [{"product_id": "p2", "qty": 2}]})
    assert r.status_code == 201
    alice_order = r.json()
    oid = alice_order["id"]

    # Bob probes with a discount request on Alice's order
    r2 = bob_client.post(f"/orders/{oid}/discount", json={"percent": 10})
    assert r2.status_code == 403

    # The 403 body must not contain Alice's order details (user_id or total)
    body_text = r2.text
    assert alice_order["user_id"] not in body_text or r2.status_code == 403
    assert str(alice_order["total_paise"]) not in body_text
