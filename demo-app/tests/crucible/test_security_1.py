"""Security: bulk-cancel must not cancel an order belonging to a different user (IDOR, privilege escalation)."""
import app.store as store
from app.models import OrderStatus


def test_bulk_cancel_does_not_cancel_another_users_order(alice_client, bob_client):
    # Alice creates an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    alice_order_id = resp.json()["id"]

    # Bob attempts to bulk-cancel Alice's order; Alice's order must remain placed
    bob_client.post("/orders/bulk-cancel", json={"order_ids": [alice_order_id]})
    assert store.orders[alice_order_id].status == OrderStatus.placed
