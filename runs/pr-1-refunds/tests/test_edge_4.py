"""Refund on a non-existent order ID must return 404."""
from fastapi.testclient import TestClient


def test_refund_unknown_order_returns_404(alice_client: TestClient) -> None:
    # Attempt refund on an order that does not exist — must return 404
    refund_resp = alice_client.post("/orders/nonexistent-order-id/refund", json={"amount_paise": 500})
    assert refund_resp.status_code == 404
