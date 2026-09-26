"""Sending order_ids as a non-list type must not return a 5xx response."""
from __future__ import annotations


def test_bulk_cancel_non_list_order_ids_no_5xx(alice_client):
    # Send order_ids as a string instead of a list
    resp = alice_client.post("/orders/bulk-cancel", json={"order_ids": "not-a-list"})
    assert resp.status_code < 500
