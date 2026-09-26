"""Sending an empty JSON body (missing order_ids field) to bulk-cancel must return 400."""
from __future__ import annotations


def test_bulk_cancel_missing_order_ids_field_returns_400(alice_client):
    # Omit the order_ids field entirely
    resp = alice_client.post("/orders/bulk-cancel", json={})
    assert resp.status_code == 400
