"""Feature tests for the bulk-cancel endpoint (happy paths and correct-behaviour checks)."""
from __future__ import annotations

import app.store as store


def _place(client, qty=1):
    """Place an order for p1; return the order id."""
    resp = client.post("/orders", json={"items": [{"product_id": "p1", "qty": qty}]})
    return resp.json()["id"]


def test_bulk_cancel_returns_200(alice_client):
    oid = _place(alice_client)
    resp = alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})
    assert resp.status_code == 200


def test_bulk_cancel_reports_cancelled_ids(alice_client):
    oid = _place(alice_client)
    resp = alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})
    assert oid in resp.json()["cancelled"]


def test_bulk_cancel_count_matches(alice_client):
    oid1 = _place(alice_client)
    oid2 = _place(alice_client)
    resp = alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid1, oid2]})
    assert resp.json()["cancelled_count"] == 2


def test_bulk_cancel_restores_stock(alice_client):
    stock_before = store.products["p1"].stock
    oid = _place(alice_client, qty=3)
    alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})
    assert store.products["p1"].stock == stock_before


def test_bulk_cancel_skips_delivered_order(alice_client):
    oid = _place(alice_client)
    alice_client.post(f"/orders/{oid}/deliver")
    resp = alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})
    assert oid in resp.json()["skipped"]
    assert resp.json()["cancelled_count"] == 0


def test_bulk_cancel_empty_list_returns_400(alice_client):
    resp = alice_client.post("/orders/bulk-cancel", json={"order_ids": []})
    assert resp.status_code == 400


def test_bulk_cancel_unknown_id_is_skipped(alice_client):
    resp = alice_client.post("/orders/bulk-cancel", json={"order_ids": ["no_such_order"]})
    assert resp.status_code == 200
    assert "no_such_order" in resp.json()["skipped"]


def test_bulk_cancel_mixed_placed_and_delivered(alice_client):
    oid_placed = _place(alice_client)
    oid_delivered = _place(alice_client)
    alice_client.post(f"/orders/{oid_delivered}/deliver")
    resp = alice_client.post(
        "/orders/bulk-cancel",
        json={"order_ids": [oid_placed, oid_delivered]},
    )
    data = resp.json()
    assert oid_placed in data["cancelled"]
    assert oid_delivered in data["skipped"]
    assert data["cancelled_count"] == 1
