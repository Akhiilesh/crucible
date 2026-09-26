"""After a successful refund, the order status must be 'refunded' and refunded_paise must match the request."""
from fastapi.testclient import TestClient


def test_refund_status_and_amount_recorded(alice_client: TestClient) -> None:
    """A successful refund sets status to 'refunded' and records the refunded_paise amount."""
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]
    total = resp.json()["total_paise"]

    alice_client.post(f"/orders/{oid}/deliver")

    amount = total  # refund the full amount
    r = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": amount})
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "refunded"
    assert body.get("refunded_paise") == amount
