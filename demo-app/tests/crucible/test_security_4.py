"""Security: bulk-cancel must return 403 when the caller does not own the target order (R8)."""
import app.store as store
from app.models import OrderStatus


def test_bulk_cancel_returns_403_for_unowned_order(alice_client, bob_client):
    # Alice creates an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p2", "qty": 1}]})
    assert resp.status_code == 201
    alice_order_id = resp.json()["id"]

    # Bob sends bulk-cancel with Alice's order ID — must get 403
    resp = bob_client.post("/orders/bulk-cancel", json={"order_ids": [alice_order_id]})
    assert resp.status_code == 403
