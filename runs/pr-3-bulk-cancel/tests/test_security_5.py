"""Security: bulk-cancel with a header injection value must not return 500 or expose internal state."""
from fastapi.testclient import TestClient
from app.main import app


def test_bulk_cancel_header_injection_does_not_cause_500():
    injection_client = TestClient(app, raise_server_exceptions=False, headers={"x-user-id": "u1\x00evil"})
    resp = injection_client.post("/orders/bulk-cancel", json={"order_ids": ["o1"]})
    assert resp.status_code != 500
    body = resp.text
    assert "traceback" not in body.lower()
    assert "exception" not in body.lower()
