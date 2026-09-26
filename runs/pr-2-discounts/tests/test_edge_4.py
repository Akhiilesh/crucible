"""Edge test: applying a discount to an order owned by another user must return 403."""


def test_discount_by_non_owner_returns_403(alice_client, bob_client):
    # Alice creates an order
    r = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert r.status_code == 201
    order_id = r.json()["id"]

    # Bob (non-owner) attempts to apply a discount to Alice's order
    r2 = bob_client.post(f"/orders/{order_id}/discount", json={"percent": 10})
    assert r2.status_code == 403
