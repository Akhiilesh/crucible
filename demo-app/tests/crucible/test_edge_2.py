"""Duplicate order IDs in the bulk-cancel list must not cause an order ID to appear in both cancelled and skipped."""
from __future__ import annotations


def test_bulk_cancel_duplicate_id_not_in_both_lists(alice_client):
    # Place one order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    # Submit the same order ID twice
    resp = alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid, oid]})
    assert resp.status_code == 200
    data = resp.json()

    # An order ID must appear in at most one of the two lists
    assert oid not in data["cancelled"] or oid not in data["skipped"], (
        "An order ID must not appear in both cancelled and skipped"
    )
