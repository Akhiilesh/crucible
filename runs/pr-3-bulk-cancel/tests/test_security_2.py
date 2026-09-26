"""Security: bulk-cancel with a missing X-User-Id header must return 401 or 422, not 2xx or 500."""


def test_bulk_cancel_missing_user_header(alice_client):
    # Use a plain client with no user header
    from fastapi.testclient import TestClient
    from app.main import app
    plain_client = TestClient(app, raise_server_exceptions=False)

    resp = plain_client.post("/orders/bulk-cancel", json={"order_ids": ["o1"]})
    assert resp.status_code in (401, 422)
