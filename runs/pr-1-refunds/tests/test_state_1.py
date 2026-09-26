"""A refunded order cannot be refunded again; the second request must return 400."""
import pytest
from fastapi.testclient import TestClient

import app.store as store


def test_double_refund_rejected(alice_client: TestClient) -> None:
    """Refunding the same delivered order twice must return 400 on the second attempt."""
    # Create and deliver an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    alice_client.post(f"/orders/{oid}/deliver")

    # First refund — must succeed
    r1 = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 100})
    assert r1.status_code == 200

    # Second refund on the same order — must be rejected
    r2 = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 100})
    assert r2.status_code == 400
