"""R18: Refund amount must be greater than 0 and at most the order total."""
import app.store as store


def test_refund_amount_exceeding_total_returns_400(alice_client):
    # Create and deliver an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]
    total = resp.json()["total_paise"]

    alice_client.post(f"/orders/{oid}/deliver")

    # Refund more than the order total — must return 400
    refund_resp = alice_client.post(
        f"/orders/{oid}/refund", json={"amount_paise": total + 1}
    )
    assert refund_resp.status_code == 400
