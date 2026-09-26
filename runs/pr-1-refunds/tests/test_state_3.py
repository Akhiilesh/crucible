"""A cancelled order cannot be refunded; it must return 400."""
from fastapi.testclient import TestClient


def test_refund_cancelled_order_rejected(alice_client: TestClient) -> None:
    """Attempting to refund a cancelled order must return 400."""
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    # Cancel the order first
    cancel_resp = alice_client.post(f"/orders/{oid}/cancel")
    assert cancel_resp.status_code == 200

    # Refunding a cancelled order must be rejected
    r = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 100})
    assert r.status_code == 400
