"""Edge test: discount percent of 51 must return 400 (above valid range 1-50)."""


def test_discount_percent_51_returns_400(alice_client):
    # Create an order for Alice
    r = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert r.status_code == 201
    order_id = r.json()["id"]

    # Apply discount with percent=51, which is above the valid range of 1-50
    r2 = alice_client.post(f"/orders/{order_id}/discount", json={"percent": 51})
    assert r2.status_code == 400
