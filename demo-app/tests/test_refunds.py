"""Feature tests for the refund endpoint (happy paths and correct-behaviour checks)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import app.store as store


# ── Helpers ──────────────────────────────────────────────────────────────────

def _delivered_order(client):
    """Place and deliver an order; return the order id."""
    resp = client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    oid = resp.json()["id"]
    client.post(f"/orders/{oid}/deliver")
    return oid


def _backdate_delivery(oid: str, days_ago: int) -> None:
    """Move delivered_at back by days_ago days (direct store edit, no mocking)."""
    past = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    store.orders[oid] = store.orders[oid].model_copy(update={"delivered_at": past})


# ── Tests ────────────────────────────────────────────────────────────────────

def test_refund_delivered_order_returns_200(alice_client):
    oid = _delivered_order(alice_client)
    resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 1000})
    assert resp.status_code == 200


def test_refund_sets_status_to_refunded(alice_client):
    oid = _delivered_order(alice_client)
    resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 1000})
    assert resp.json()["status"] == "refunded"


def test_refund_records_refunded_paise(alice_client):
    oid = _delivered_order(alice_client)
    resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 500})
    assert resp.json()["refunded_paise"] == 500


def test_refund_within_14_days_succeeds(alice_client):
    oid = _delivered_order(alice_client)
    resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 1000})
    assert resp.status_code == 200


def test_refund_placed_order_returns_400(alice_client):
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    oid = resp.json()["id"]
    resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 1000})
    assert resp.status_code == 400


def test_refund_zero_amount_returns_400(alice_client):
    oid = _delivered_order(alice_client)
    resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 0})
    assert resp.status_code == 400


def test_refund_amount_exceeds_total_returns_400(alice_client):
    oid = _delivered_order(alice_client)
    resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 999999})
    assert resp.status_code == 400


def test_double_refund_returns_400(alice_client):
    oid = _delivered_order(alice_client)
    alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 1000})
    resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 1000})
    assert resp.status_code == 400


def test_refund_other_users_order_returns_403(alice_client, bob_client):
    oid = _delivered_order(alice_client)
    resp = bob_client.post(f"/orders/{oid}/refund", json={"amount_paise": 1000})
    assert resp.status_code == 403
