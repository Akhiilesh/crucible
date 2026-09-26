"""R19: A refunded order cannot be refunded again."""
import app.store as store


def test_double_refund_returns_400(alice_client):
    # Create and deliver an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    alice_client.post(f"/orders/{oid}/deliver")

    # First refund succeeds
    first = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 500})
    assert first.status_code == 200

    # Second refund on the same order must be rejected
    second = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 500})
    assert second.status_code == 400
