"""Bulk cancel must return 400 when the order_ids list is empty (R26)."""
from __future__ import annotations


def test_bulk_cancel_empty_list_returns_400(alice_client):
    resp = alice_client.post("/orders/bulk-cancel", json={"order_ids": []})
    assert resp.status_code == 400
