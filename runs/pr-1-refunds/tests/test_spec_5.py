"""R20: A successful refund sets the order status to 'refunded' and returns 200."""
import app.store as store


def test_successful_refund_returns_200_with_refunded_status(alice_client):
    # Create and deliver an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    alice_client.post(f"/orders/{oid}/deliver")

    # Valid refund within window
    refund_resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 500})
    assert refund_resp.status_code == 200
    assert refund_resp.json().get("status") == "refunded"
