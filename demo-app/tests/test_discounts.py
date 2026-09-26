"""Feature tests for the discount endpoint (happy paths and correct-behaviour checks)."""
from __future__ import annotations


def _placed_order(client, qty=2):
    """Place an order for p1 (1000 paise each); return (order_id, total_paise)."""
    resp = client.post("/orders", json={"items": [{"product_id": "p1", "qty": qty}]})
    data = resp.json()
    return data["id"], data["total_paise"]


def test_apply_discount_returns_200(alice_client):
    oid, _ = _placed_order(alice_client)
    resp = alice_client.post(f"/orders/{oid}/discount", json={"percent": 10})
    assert resp.status_code == 200


def test_discount_reduces_total(alice_client):
    oid, total = _placed_order(alice_client, qty=2)  # 2000 paise
    resp = alice_client.post(f"/orders/{oid}/discount", json={"percent": 10})
    expected = total - (total * 10 // 100)
    assert resp.json()["total_paise"] == expected


def test_discount_records_percent(alice_client):
    oid, _ = _placed_order(alice_client)
    resp = alice_client.post(f"/orders/{oid}/discount", json={"percent": 25})
    assert resp.json()["discount_percent"] == 25


def test_discount_50_percent_halves_total(alice_client):
    oid, total = _placed_order(alice_client, qty=4)  # 4000 paise
    resp = alice_client.post(f"/orders/{oid}/discount", json={"percent": 50})
    assert resp.json()["total_paise"] == total // 2


def test_discount_total_never_below_zero(alice_client):
    oid, _ = _placed_order(alice_client, qty=1)
    resp = alice_client.post(f"/orders/{oid}/discount", json={"percent": 50})
    assert resp.json()["total_paise"] >= 0


def test_discount_zero_percent_returns_400(alice_client):
    oid, _ = _placed_order(alice_client)
    resp = alice_client.post(f"/orders/{oid}/discount", json={"percent": 0})
    assert resp.status_code == 400


def test_discount_51_percent_returns_400(alice_client):
    oid, _ = _placed_order(alice_client)
    resp = alice_client.post(f"/orders/{oid}/discount", json={"percent": 51})
    assert resp.status_code == 400


def test_discount_other_users_order_returns_403(alice_client, bob_client):
    oid, _ = _placed_order(alice_client)
    resp = bob_client.post(f"/orders/{oid}/discount", json={"percent": 10})
    assert resp.status_code == 403


def test_discount_minimum_1_percent_accepted(alice_client):
    oid, _ = _placed_order(alice_client)
    resp = alice_client.post(f"/orders/{oid}/discount", json={"percent": 1})
    assert resp.status_code == 200
