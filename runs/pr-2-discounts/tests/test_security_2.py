"""POST /orders/{id}/discount without X-User-Id must return 422, not 500."""
from fastapi.testclient import TestClient
from app.main import app


def test_discount_missing_user_header():
    # Use a plain client with no default headers
    client = TestClient(app, raise_server_exceptions=False)

    # First create an order as alice so we have a real order id
    alice = TestClient(app, raise_server_exceptions=False, headers={"x-user-id": "u1"})
    r = alice.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert r.status_code == 201
    oid = r.json()["id"]

    # Now call without any user header
    r2 = client.post(f"/orders/{oid}/discount", json={"percent": 10})
    assert r2.status_code in (401, 422)
    assert r2.status_code != 500
