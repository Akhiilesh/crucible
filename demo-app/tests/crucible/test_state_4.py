"""A refund request more than 14 days after delivered_at must return 400."""
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

import app.store as store


def test_refund_outside_window_from_delivered_at_rejected(alice_client: TestClient) -> None:
    """The 14-day refund window is counted from delivered_at; a request 15 days after
    delivered_at must return 400 even if the order was created recently."""
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    alice_client.post(f"/orders/{oid}/deliver")

    # Backdate delivered_at to 15 days ago, keep created_at recent
    now = datetime.now(tz=timezone.utc)
    store.orders[oid] = store.orders[oid].model_copy(update={
        "delivered_at": now - timedelta(days=15),
        "created_at": now - timedelta(days=1),
    })

    r = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 100})
    assert r.status_code == 400
