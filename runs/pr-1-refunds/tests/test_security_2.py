"""Test that a refund request with no X-User-Id header returns 401 or 422."""


def test_refund_without_user_header_returns_4xx(client):
    # Create and deliver an order using alice
    from fastapi.testclient import TestClient
    from app.main import app
    import app.store as store

    alice = TestClient(app, raise_server_exceptions=False, headers={"x-user-id": "u1"})
    resp = alice.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]
    alice.post(f"/orders/{oid}/deliver")

    # Attempt a refund with no user header — must not succeed
    resp = client.post(f"/orders/{oid}/refund", json={"amount_paise": 100})
    assert resp.status_code in (401, 422)
