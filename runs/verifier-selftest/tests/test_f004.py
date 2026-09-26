"""F-004 — Fake: pre-existing failure — qty=0 returns 422 on both main and pr-1-refunds.

Pydantic validation rejects qty < 1 (R2) with a 422 before the app logic runs.
This test fails on the base branch (main) too — it is not introduced by the PR.
No refund routes or function names are referenced, so G2 cannot claim new_code.
"""
from __future__ import annotations


def test_create_order_qty_zero_returns_400(alice_client):
    # The app returns 422 (Pydantic validation), not 400 — fails on main too
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 0}]})
    assert resp.status_code == 400
