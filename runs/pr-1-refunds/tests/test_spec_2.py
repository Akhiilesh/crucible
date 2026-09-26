"""R15: Refunds are only allowed for orders with status 'delivered'."""
import app.store as store


def test_refund_placed_order_returns_400(alice_client):
    # Place an order but do not deliver it
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    # Attempt to refund a placed order — must return 400
    refund_resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 500})
    assert refund_resp.status_code == 400
