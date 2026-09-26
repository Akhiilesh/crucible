"""Tests for the base orders service (Phase 1.1 — no feature branches)."""
from __future__ import annotations

import app.store as store


# ── Helpers ──────────────────────────────────────────────────────────────────

def _place_order(client, items=None):
    """Place a simple order for Alice and return the response."""
    if items is None:
        items = [{"product_id": "p1", "qty": 2}]
    return client.post("/orders", json={"items": items})


# ── Order creation ────────────────────────────────────────────────────────────

def test_create_order_returns_201(alice_client):
    resp = _place_order(alice_client)
    assert resp.status_code == 201


def test_create_order_total_is_computed(alice_client):
    # p1 = 1000 paise each, qty=3 → total = 3000
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 3}]})
    assert resp.status_code == 201
    assert resp.json()["total_paise"] == 3000


def test_create_order_reduces_stock(alice_client):
    stock_before = store.products["p1"].stock
    _place_order(alice_client, items=[{"product_id": "p1", "qty": 5}])
    assert store.products["p1"].stock == stock_before - 5


def test_create_order_multiple_items(alice_client):
    resp = alice_client.post(
        "/orders",
        json={"items": [{"product_id": "p1", "qty": 1}, {"product_id": "p2", "qty": 2}]},
    )
    assert resp.status_code == 201
    # p1=1000, p2=2500×2=5000 → total=6000
    assert resp.json()["total_paise"] == 6000


def test_create_order_status_is_placed(alice_client):
    resp = _place_order(alice_client)
    assert resp.json()["status"] == "placed"


def test_create_order_insufficient_stock_returns_400(alice_client):
    resp = alice_client.post(
        "/orders", json={"items": [{"product_id": "p1", "qty": 9999}]}
    )
    assert resp.status_code == 400


def test_create_order_unknown_product_returns_404(alice_client):
    resp = alice_client.post(
        "/orders", json={"items": [{"product_id": "no_such_product", "qty": 1}]}
    )
    assert resp.status_code == 404


def test_create_order_stock_not_reduced_on_failure(alice_client):
    """Stock must not be reduced if the order fails validation."""
    stock_before = store.products["p1"].stock
    alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 9999}]})
    assert store.products["p1"].stock == stock_before


def test_create_order_unknown_user_returns_401(client):
    resp = client.post(
        "/orders",
        json={"items": [{"product_id": "p1", "qty": 1}]},
        headers={"x-user-id": "unknown"},
    )
    assert resp.status_code == 401


# ── Get order ─────────────────────────────────────────────────────────────────

def test_get_own_order(alice_client):
    order_id = _place_order(alice_client).json()["id"]
    resp = alice_client.get(f"/orders/{order_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


def test_get_other_users_order_returns_403(alice_client, bob_client):
    order_id = _place_order(alice_client).json()["id"]
    resp = bob_client.get(f"/orders/{order_id}")
    assert resp.status_code == 403


def test_get_nonexistent_order_returns_404(alice_client):
    resp = alice_client.get("/orders/does_not_exist")
    assert resp.status_code == 404


# ── Deliver ───────────────────────────────────────────────────────────────────

def test_deliver_placed_order(alice_client):
    order_id = _place_order(alice_client).json()["id"]
    resp = alice_client.post(f"/orders/{order_id}/deliver")
    assert resp.status_code == 200
    assert resp.json()["status"] == "delivered"
    assert resp.json()["delivered_at"] is not None


def test_deliver_sets_delivered_at(alice_client):
    order_id = _place_order(alice_client).json()["id"]
    resp = alice_client.post(f"/orders/{order_id}/deliver")
    assert resp.json()["delivered_at"] is not None


def test_cannot_deliver_cancelled_order(alice_client):
    order_id = _place_order(alice_client).json()["id"]
    alice_client.post(f"/orders/{order_id}/cancel")
    resp = alice_client.post(f"/orders/{order_id}/deliver")
    assert resp.status_code == 400


# ── Cancel ────────────────────────────────────────────────────────────────────

def test_cancel_placed_order(alice_client):
    order_id = _place_order(alice_client).json()["id"]
    resp = alice_client.post(f"/orders/{order_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_cancel_restores_stock(alice_client):
    stock_before = store.products["p1"].stock
    order_id = _place_order(alice_client, items=[{"product_id": "p1", "qty": 3}]).json()["id"]
    alice_client.post(f"/orders/{order_id}/cancel")
    assert store.products["p1"].stock == stock_before


def test_cannot_cancel_delivered_order(alice_client):
    order_id = _place_order(alice_client).json()["id"]
    alice_client.post(f"/orders/{order_id}/deliver")
    resp = alice_client.post(f"/orders/{order_id}/cancel")
    assert resp.status_code == 400


def test_cannot_cancel_already_cancelled_order(alice_client):
    order_id = _place_order(alice_client).json()["id"]
    alice_client.post(f"/orders/{order_id}/cancel")
    resp = alice_client.post(f"/orders/{order_id}/cancel")
    assert resp.status_code == 400


def test_cancel_other_users_order_returns_403(alice_client, bob_client):
    order_id = _place_order(alice_client).json()["id"]
    resp = bob_client.post(f"/orders/{order_id}/cancel")
    assert resp.status_code == 403
