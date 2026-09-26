"""Security: bulk-cancel with an unknown X-User-Id must return 401, not 2xx or 500."""
from fastapi.testclient import TestClient
from app.main import app


def test_bulk_cancel_unknown_user_returns_401():
    unknown_client = TestClient(app, raise_server_exceptions=False, headers={"x-user-id": "unknown-user-999"})
    resp = unknown_client.post("/orders/bulk-cancel", json={"order_ids": ["o1"]})
    assert resp.status_code == 401
