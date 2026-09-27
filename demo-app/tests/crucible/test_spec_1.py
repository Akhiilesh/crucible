"""R16: The 14-day refund window is counted from delivered_at, not created_at."""
import pytest
from datetime import datetime, timedelta, timezone
import app.store as store


def test_refund_window_counted_from_delivered_at(alice_client):
    # Create and deliver an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    deliver_resp = alice_client.post(f"/orders/{oid}/deliver")
    assert deliver_resp.status_code == 200

    # Backdate created_at to 20 days ago but delivered_at to 2 days ago.
    # Per R16, the window starts at delivered_at (2 days ago), so refund must be allowed.
    now = datetime.now(tz=timezone.utc)
    store.orders[oid] = store.orders[oid].model_copy(update={
        "created_at": now - timedelta(days=20),
        "delivered_at": now - timedelta(days=2),
    })

    resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 500})
    assert resp.status_code == 200
