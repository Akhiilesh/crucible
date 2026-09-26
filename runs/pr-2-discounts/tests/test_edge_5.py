"""Edge test: a huge discount percent (far beyond 50) must return 400."""


def test_discount_huge_percent_returns_400(alice_client):
    # Create an order for Alice
    r = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert r.status_code == 201
    order_id = r.json()["id"]

    # Apply discount with percent=2147483647 (2^31-1), far beyond the valid range 1-50
    r2 = alice_client.post(f"/orders/{order_id}/discount", json={"percent": 2147483647})
    assert r2.status_code == 400
