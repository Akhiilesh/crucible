"""After a discount, the recorded discount_percent must match the actual reduction applied to the original total."""
from __future__ import annotations

import app.store as store


def test_discount_percent_matches_actual_total_reduction(alice_client):
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 10}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]
    original_total = resp.json()["total_paise"]

    r1 = alice_client.post(f"/orders/{oid}/discount", json={"percent": 20})
    assert r1.status_code == 200
    after_first = r1.json()["total_paise"]

    # Apply a second discount
    r2 = alice_client.post(f"/orders/{oid}/discount", json={"percent": 10})
    assert r2.status_code == 200
    final_total = r2.json()["final_total"] if "final_total" in r2.json() else r2.json()["total_paise"]
    recorded_percent = r2.json()["discount_percent"]

    # The recorded discount_percent (10) must reflect that the total after both
    # discounts equals original minus (recorded_percent % of original).
    # If the implementation compounds discounts and only stores the latest percent,
    # the recorded percent is inconsistent with the actual total reduction.
    expected_from_recorded = original_total - (original_total * recorded_percent // 100)
    # The actual total must equal what the recorded percent implies from the original
    assert final_total == expected_from_recorded
