# Crucible report — `pr-2-discounts`

**4 proven** · **16 rejected** · 4 fixed · 0 unfixed · reviewed in **4m 57s**

## Scorecard

| Metric | Value |
|---|---|
| Raw suspicions (attacker findings) | 20 |
| Proven by failing test (all 4 gates) | 4 |
| Distinct fixes (root causes fixed) | 2 |
| Rejected as noise | 16 |
| Fixed (proof test now passes 3/3) | 4 |
| Unfixed | 0 |
| Precision of reported findings | 100% (4 of 4 carry a failing proof test) |
| Suspicions confirmed | 20% (4 of 20) |
| Full suite after fixes | green — 33 passed, 1 warning in 0.08s (`5d34019`) |

### Time per stage

| Stage | Seconds | By |
|---|---|---|
| intent | 47 | bob |
| attack | 233 | bob-subagents |
| verify | 10 | crucible-cli |
| fix | 3 | claude-code |
| verify_after_fix | 4 | crucible-cli |
| **total** | **297** | |

Attack mode: **parallel** (4 lenses).

## Proven findings

### F-011 · state — Applying a discount to an order that already has a discount must not compound the reduction a second time.

- **Basis:** `no_double_effect` — "Repeating a request never applies its effect twice."
- **Red → green:** fails on PR 3/3 → passes after fix 3/3
- **Fix commit:** `031c523`

<details><summary>Proof test (runs/pr-2-discounts/tests/test_state_1.py)</summary>

```python
"""Applying a discount to the same order twice must not apply the effect twice."""
from __future__ import annotations


def test_discount_cannot_be_applied_twice(alice_client):
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 4}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]
    original_total = resp.json()["total_paise"]

    # First discount: 10% off
    r1 = alice_client.post(f"/orders/{oid}/discount", json={"percent": 10})
    assert r1.status_code == 200
    after_first = r1.json()["total_paise"]
    expected_after_first = original_total - (original_total * 10 // 100)
    assert after_first == expected_after_first

    # Second discount: must be rejected (or be a no-op) — must not compound
    r2 = alice_client.post(f"/orders/{oid}/discount", json={"percent": 10})
    # Either the second call is rejected or the total remains the same as after the first
    assert r2.status_code != 200 or r2.json()["total_paise"] == after_first
```

</details>

```diff
diff --git a/demo-app/app/main.py b/demo-app/app/main.py
index bdaa29b..895968b 100644
--- a/demo-app/app/main.py
+++ b/demo-app/app/main.py
@@ -135,8 +135,11 @@ def apply_discount(
             detail="Discount percent must be between 1 and 50 inclusive",
         )
 
-    discount_amount = (order.total_paise * body.percent) // 100
-    new_total = max(0, order.total_paise - discount_amount)
+    original_total = sum(
+        store.products[item.product_id].price_paise * item.qty for item in order.items
+    )
+    discount_amount = (original_total * body.percent) // 100
+    new_total = max(0, original_total - discount_amount)
 
     updated = order.model_copy(update={
         "total_paise": new_total,
```

### F-012 · state — Attempting to apply a discount to a delivered order must return 400.

- **Basis:** `spec/orders.md#R21` — "A discount code gives a percentage off the order total, between 1 and 50 inclusive."
- **Red → green:** fails on PR 3/3 → passes after fix 3/3
- **Fix commit:** `ce337cb`

<details><summary>Proof test (runs/pr-2-discounts/tests/test_state_2.py)</summary>

```python
"""Applying a discount to a delivered order must be rejected with 400."""
from __future__ import annotations


def test_discount_on_delivered_order_returns_400(alice_client):
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    # Deliver the order
    r_deliver = alice_client.post(f"/orders/{oid}/deliver")
    assert r_deliver.status_code == 200
    assert r_deliver.json()["status"] == "delivered"

    # Attempting to discount a delivered order must be rejected
    r_discount = alice_client.post(f"/orders/{oid}/discount", json={"percent": 10})
    assert r_discount.status_code == 400
```

</details>

```diff
diff --git a/demo-app/app/main.py b/demo-app/app/main.py
index 895968b..d3c2702 100644
--- a/demo-app/app/main.py
+++ b/demo-app/app/main.py
@@ -129,6 +129,12 @@ def apply_discount(
     user_id = _require_user(x_user_id)
     order = _require_own_order(order_id, user_id)
 
+    if order.status != OrderStatus.placed:
+        raise HTTPException(
+            status_code=400,
+            detail=f"Cannot discount an order with status {order.status!r}",
+        )
+
     if body.percent < 1 or body.percent > 50:
         raise HTTPException(
             status_code=400,
```

### F-013 · state — Attempting to apply a discount to a cancelled order must return 400.

- **Basis:** `spec/orders.md#R21` — "A discount code gives a percentage off the order total, between 1 and 50 inclusive."
- **Red → green:** fails on PR 3/3 → passes after fix 3/3
- **Fix commit:** `ce337cb` (same root cause as F-012)

<details><summary>Proof test (runs/pr-2-discounts/tests/test_state_3.py)</summary>

```python
"""Applying a discount to a cancelled order must be rejected with 400."""
from __future__ import annotations


def test_discount_on_cancelled_order_returns_400(alice_client):
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    # Cancel the order
    r_cancel = alice_client.post(f"/orders/{oid}/cancel")
    assert r_cancel.status_code == 200
    assert r_cancel.json()["status"] == "cancelled"

    # Attempting to discount a cancelled order must be rejected
    r_discount = alice_client.post(f"/orders/{oid}/discount", json={"percent": 10})
    assert r_discount.status_code == 400
```

</details>


### F-014 · state — The discount_percent recorded on the order must reflect the actual percentage reduction applied to the original order total.

- **Basis:** `spec/orders.md#R21` — "A discount code gives a percentage off the order total, between 1 and 50 inclusive."
- **Red → green:** fails on PR 3/3 → passes after fix 3/3
- **Fix commit:** `031c523` (same root cause as F-011)

<details><summary>Proof test (runs/pr-2-discounts/tests/test_state_4.py)</summary>

```python
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
```

</details>


## Noise rejected (16)

<details><summary>Show rejected findings</summary>

**does not fail on PR** (16)

- F-001 · edge · `spec/orders.md#R24` — A discount percent of 0 is outside the valid range 1-50 and must return 400.
- F-002 · edge · `spec/orders.md#R24` — A discount percent of 51 is outside the valid range 1-50 and must return 400.
- F-003 · edge · `spec/orders.md#R24` — A negative discount percent is outside the valid range 1-50 and must return 400.
- F-004 · edge · `spec/orders.md#R22` — A discount can only be applied by the owner of the order; any other caller must receive 403.
- F-005 · edge · `spec/orders.md#R24` — A discount percent far above 50 is outside the valid range and must return 400.
- F-006 · security · `spec/orders.md#R22` — A discount can only be applied by the owner of the order; any other user must receive 403.
- F-007 · security · `no_5xx` — Calling POST /orders/{id}/discount without the X-User-Id header must return 422, not 500.
- F-008 · security · `spec/orders.md#R7` — Calling POST /orders/{id}/discount with an unknown X-User-Id must return 401.
- F-009 · security · `no_data_leak` — A 403 response from POST /orders/{id}/discount must not expose the order total or other user data.
- F-010 · security · `no_5xx` — POST /orders/{id}/discount with a null-byte or special-character X-User-Id must not return 500.
- F-015 · state · `spec/orders.md#R21` — Applying a discount to one order must leave every other order's total and discount_percent completely unchanged.
- F-016 · spec · `spec/orders.md#R24` — A discount percentage of 0 is outside the range 1–50 and must return 400.
- F-017 · spec · `spec/orders.md#R24` — A discount percentage of 51 is outside the range 1–50 and must return 400.
- F-018 · spec · `spec/orders.md#R22` — A discount can only be applied by the owner of the order; any other caller must receive 403.
- F-019 · spec · `spec/orders.md#R21` — A discount percentage of 1 is the minimum valid value and must be accepted with a 200 response.
- F-020 · spec · `spec/orders.md#R23` — The order total after a discount can never go below 0.

</details>