"""Edge test: discount percent of 0 must return 400 (below valid range 1-50)."""
import pytest
from app.main import app
from fastapi.testclient import TestClient


def test_discount_percent_zero_returns_400(alice_client):
    # Create an order for Alice
    r = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert r.status_code == 201
    order_id = r.json()["id"]

    # Apply discount with percent=0, which is below the valid range of 1-50
    r2 = alice_client.post(f"/orders/{order_id}/discount", json={"percent": 0})
    assert r2.status_code == 400
