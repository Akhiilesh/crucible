"""Edge test: discount percent of -1 must return 400 (negative, below valid range)."""


def test_discount_percent_negative_returns_400(alice_client):
    # Create an order for Alice
    r = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert r.status_code == 201
    order_id = r.json()["id"]

    # Apply discount with percent=-1, which is negative and outside valid range 1-50
    r2 = alice_client.post(f"/orders/{order_id}/discount", json={"percent": -1})
    assert r2.status_code == 400
