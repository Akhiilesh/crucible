"""POST /orders/{id}/discount with an unknown X-User-Id must return 401, not 200 or 500."""
from fastapi.testclient import TestClient
from app.main import app


def test_discount_unknown_user_returns_401():
    alice = TestClient(app, raise_server_exceptions=False, headers={"x-user-id": "u1"})
    r = alice.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert r.status_code == 201
    oid = r.json()["id"]

    unknown = TestClient(app, raise_server_exceptions=False, headers={"x-user-id": "unknown-user-999"})
    r2 = unknown.post(f"/orders/{oid}/discount", json={"percent": 10})
    assert r2.status_code == 401
