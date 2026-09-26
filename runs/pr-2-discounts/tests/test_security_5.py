"""POST /orders/{id}/discount with a special-character X-User-Id must not return 500."""
from fastapi.testclient import TestClient
from app.main import app


def test_discount_header_injection_no_500():
    alice = TestClient(app, raise_server_exceptions=False, headers={"x-user-id": "u1"})
    r = alice.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert r.status_code == 201
    oid = r.json()["id"]

    # Attempt header injection with special characters
    injected = TestClient(app, raise_server_exceptions=False, headers={"x-user-id": "u1\x00evil"})
    r2 = injected.post(f"/orders/{oid}/discount", json={"percent": 10})
    assert r2.status_code != 500
    assert r2.status_code != 200
