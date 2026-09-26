"""A discount applied by a non-owner must return 403 (IDOR on POST /orders/{id}/discount)."""
import app.store as store


def test_non_owner_cannot_apply_discount(alice_client, bob_client):
    # Alice creates an order
    r = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert r.status_code == 201
    oid = r.json()["id"]

    # Bob attempts to apply a discount to Alice's order
    r2 = bob_client.post(f"/orders/{oid}/discount", json={"percent": 10})
    assert r2.status_code == 403
