# Crucible report — `pr-3-bulk-cancel`

**10 proven** · **10 rejected** · 7 fixed · 3 unfixed · reviewed in **2m 55s**

## Scorecard

| Metric | Value |
|---|---|
| Raw suspicions (attacker findings) | 20 |
| Proven by failing test (all 4 gates) | 10 |
| Distinct fixes (root causes fixed) | 3 |
| Rejected as noise | 10 |
| Fixed (proof test now passes 3/3) | 7 |
| Unfixed | 3 |
| Precision of reported findings | 100% (10 of 10 carry a failing proof test) |
| Suspicions confirmed | 50% (10 of 20) |
| Full suite after fixes | green — 35 passed, 1 warning in 0.08s (`f09a0f8`) |

### Time per stage

| Stage | Seconds | By |
|---|---|---|
| intent | 16 | bob |
| attack | 98 | bob-subagents |
| verify | 15 | crucible-cli |
| fix | 37 | claude-code |
| verify_after_fix | 9 | crucible-cli |
| **total** | **175** | |

Attack mode: **parallel** (4 lenses).

## Proven findings

### F-001 · edge — A user must not be able to bulk-cancel orders that belong to another user.

- **Basis:** `spec/orders.md#R8` — "Accessing another user's order returns 403."
- **Red → green:** fails on PR 3/3 → passes after fix 3/3
- **Fix commit:** `4e542ed`

<details><summary>Proof test (runs/pr-3-bulk-cancel/tests/test_edge_1.py)</summary>

```python
"""A user must not be able to bulk-cancel orders belonging to another user."""
from __future__ import annotations

import app.store as store


def test_bulk_cancel_cannot_cancel_another_users_order(alice_client, bob_client):
    # Alice places an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    # Bob attempts to bulk-cancel Alice's order
    resp = bob_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})
    # The order must NOT be cancelled — a 403 or the order must remain in the skipped list
    # with the order still in placed status
    order = store.orders.get(oid)
    assert order is not None
    assert order.status.value == "placed", (
        "Another user's order must not be cancelled via bulk-cancel"
    )
```

</details>

```diff
diff --git a/demo-app/app/main.py b/demo-app/app/main.py
index e98fe09..86443d0 100644
--- a/demo-app/app/main.py
+++ b/demo-app/app/main.py
@@ -126,11 +126,16 @@ def bulk_cancel_orders(
     x_user_id: str = Header(...),
 ) -> BulkCancelResponse:
     """Cancel multiple placed orders in one request. Restores stock for each."""
-    _require_user(x_user_id)
+    user_id = _require_user(x_user_id)
 
     if not body.order_ids:
         raise HTTPException(status_code=400, detail="order_ids must not be empty")
 
+    for order_id in body.order_ids:
+        order = store.get_order(order_id)
+        if order is not None and order.user_id != user_id:
+            raise HTTPException(status_code=403, detail="Forbidden")
+
     cancelled: list[str] = []
     skipped: list[str] = []
```

### F-002 · edge — When the same order ID appears more than once in the bulk-cancel list, it must not appear in both the cancelled and skipped response arrays.

- **Basis:** `spec/orders.md#R28` — "Orders that are not in "placed" status are silently skipped during bulk cancel."
- **Red → green:** fails on PR 3/3 → passes after fix 3/3
- **Fix commit:** `10ff45f`

<details><summary>Proof test (runs/pr-3-bulk-cancel/tests/test_edge_2.py)</summary>

```python
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
```

</details>

```diff
diff --git a/demo-app/app/main.py b/demo-app/app/main.py
index 86443d0..dbebb4a 100644
--- a/demo-app/app/main.py
+++ b/demo-app/app/main.py
@@ -139,7 +139,7 @@ def bulk_cancel_orders(
     cancelled: list[str] = []
     skipped: list[str] = []
 
-    for order_id in body.order_ids:
+    for order_id in dict.fromkeys(body.order_ids):
         order = store.get_order(order_id)
         if order is None or order.status != OrderStatus.placed:
             skipped.append(order_id)
```

### F-003 · edge — Sending a bulk-cancel request with the order_ids field absent must return 400.

- **Basis:** `spec/orders.md#R26` — "An empty list of order IDs must return 400."
- **Red → green:** fails on PR 3/3 → passes after fix 3/3
- **Fix commit:** `ff01544`

<details><summary>Proof test (runs/pr-3-bulk-cancel/tests/test_edge_3.py)</summary>

```python
"""Sending an empty JSON body (missing order_ids field) to bulk-cancel must return 400."""
from __future__ import annotations


def test_bulk_cancel_missing_order_ids_field_returns_400(alice_client):
    # Omit the order_ids field entirely
    resp = alice_client.post("/orders/bulk-cancel", json={})
    assert resp.status_code == 400
```

</details>

```diff
diff --git a/demo-app/app/models.py b/demo-app/app/models.py
index 312840a..f72c4f8 100644
--- a/demo-app/app/models.py
+++ b/demo-app/app/models.py
@@ -49,7 +49,7 @@ class CreateOrderRequest(BaseModel):
 
 
 class BulkCancelRequest(BaseModel):
-    order_ids: list[str]
+    order_ids: list[str] = Field(default_factory=list)
 
 
 class BulkCancelResponse(BaseModel):
```

### F-004 · edge — Stock must not be restored when an unauthorized user attempts to bulk-cancel another user's order.

- **Basis:** `spec/orders.md#R27` — "Stock is restored only for orders that were actually cancelled by this request."
- **Red → green:** fails on PR 3/3 → passes after fix 3/3
- **Fix commit:** `4e542ed` (same root cause as F-001)

<details><summary>Proof test (runs/pr-3-bulk-cancel/tests/test_edge_4.py)</summary>

```python
"""Bulk-cancelling another user's placed order must not restore that order's stock."""
from __future__ import annotations

import app.store as store


def test_bulk_cancel_does_not_restore_stock_for_another_users_order(alice_client, bob_client):
    # Record stock before Alice's order
    stock_before = store.products["p1"].stock

    # Alice places an order consuming stock
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 5}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    stock_after_order = store.products["p1"].stock
    assert stock_after_order == stock_before - 5

    # Bob attempts to bulk-cancel Alice's order
    bob_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})

    # Stock must remain at the reduced level — Bob cannot restore Alice's stock
    assert store.products["p1"].stock == stock_after_order, (
        "Stock must not be restored when an unauthorized user attempts bulk-cancel"
    )
```

</details>


### F-006 · security — A user must not be able to cancel an order that belongs to another user via bulk-cancel.

- **Basis:** `spec/orders.md#R7` — "Only the user who created an order may read, modify, or cancel it."
- **Red → green:** fails on PR 3/3 → passes after fix 3/3
- **Fix commit:** `4e542ed` (same root cause as F-001)

<details><summary>Proof test (runs/pr-3-bulk-cancel/tests/test_security_1.py)</summary>

```python
"""Security: bulk-cancel must not cancel an order belonging to a different user (IDOR, privilege escalation)."""
import app.store as store
from app.models import OrderStatus


def test_bulk_cancel_does_not_cancel_another_users_order(alice_client, bob_client):
    # Alice creates an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    alice_order_id = resp.json()["id"]

    # Bob attempts to bulk-cancel Alice's order; Alice's order must remain placed
    bob_client.post("/orders/bulk-cancel", json={"order_ids": [alice_order_id]})
    assert store.orders[alice_order_id].status == OrderStatus.placed
```

</details>


### F-009 · security — Accessing another user's order via bulk-cancel must return 403.

- **Basis:** `spec/orders.md#R8` — "Accessing another user's order returns 403."
- **Red → green:** fails on PR 3/3 → passes after fix 3/3
- **Fix commit:** `4e542ed` (same root cause as F-001)

<details><summary>Proof test (runs/pr-3-bulk-cancel/tests/test_security_4.py)</summary>

```python
"""Security: bulk-cancel must return 403 when the caller does not own the target order (R8)."""
import app.store as store
from app.models import OrderStatus


def test_bulk_cancel_returns_403_for_unowned_order(alice_client, bob_client):
    # Alice creates an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p2", "qty": 1}]})
    assert resp.status_code == 201
    alice_order_id = resp.json()["id"]

    # Bob sends bulk-cancel with Alice's order ID — must get 403
    resp = bob_client.post("/orders/bulk-cancel", json={"order_ids": [alice_order_id]})
    assert resp.status_code == 403
```

</details>


### F-011 · state — Bulk-cancel must not change the status of an order that belongs to a different user.

- **Basis:** `spec/orders.md#R7` — "Only the user who created an order may read, modify, or cancel it."
- **Red → green:** fails on PR 3/3 → passes after fix 0/3
- **Fix commit:** none

- **Needs a human:** conflicts with F-009 (committed with fix 4e542ed): for another user's order id, F-009 requires 403 (R8) while this test requires 200 with the order skipped. Skipping instead of 403 turns F-009 red. Needs a human decision on bulk-cancel semantics.

<details><summary>Proof test (runs/pr-3-bulk-cancel/tests/test_state_1.py)</summary>

```python
"""Bulk-cancel must not cancel orders owned by another user."""
import app.store as store


def test_bulk_cancel_does_not_cancel_other_users_order(alice_client, bob_client):
    # Bob creates an order
    r = bob_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 2}]})
    assert r.status_code == 201
    oid = r.json()["id"]

    # Alice attempts to bulk-cancel Bob's order
    r2 = alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})
    assert r2.status_code == 200

    # Bob's order must still be in placed status
    r3 = bob_client.get(f"/orders/{oid}")
    assert r3.status_code == 200
    assert r3.json()["status"] == "placed"
```

</details>


### F-012 · state — Stock must not be restored when bulk-cancel processes an order owned by a different user.

- **Basis:** `spec/orders.md#R7` — "Only the user who created an order may read, modify, or cancel it."
- **Red → green:** fails on PR 3/3 → passes after fix 0/3
- **Fix commit:** none

- **Needs a human:** conflicts with F-009 (committed with fix 4e542ed): for another user's order id, F-009 requires 403 (R8) while this test requires 200 with the order skipped. Skipping instead of 403 turns F-009 red. Needs a human decision on bulk-cancel semantics.

<details><summary>Proof test (runs/pr-3-bulk-cancel/tests/test_state_2.py)</summary>

```python
"""Stock must not be restored when bulk-cancel skips an order belonging to another user."""
import app.store as store


def test_bulk_cancel_does_not_restore_stock_for_other_users_order(alice_client, bob_client):
    # Record initial stock
    initial_stock = store.products["p1"].stock

    # Bob creates an order consuming some stock
    r = bob_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 3}]})
    assert r.status_code == 201
    oid = r.json()["id"]

    stock_after_order = store.products["p1"].stock
    assert stock_after_order == initial_stock - 3

    # Alice attempts to bulk-cancel Bob's order
    r2 = alice_client.post("/orders/bulk-cancel", json={"order_ids": [oid]})
    assert r2.status_code == 200

    # Stock must remain reduced (not restored) since Alice does not own this order
    assert store.products["p1"].stock == stock_after_order
```

</details>


### F-015 · state — When bulk-cancel receives IDs belonging to multiple users, only the requesting user's placed orders are cancelled and have stock restored.

- **Basis:** `spec/orders.md#R27` — "Stock is restored only for orders that were actually cancelled by this request."
- **Red → green:** fails on PR 3/3 → passes after fix 0/3
- **Fix commit:** none

- **Needs a human:** conflicts with F-009 (committed with fix 4e542ed): for another user's order id, F-009 requires 403 (R8) while this test requires 200 with the order skipped. Skipping instead of 403 turns F-009 red. Needs a human decision on bulk-cancel semantics.

<details><summary>Proof test (runs/pr-3-bulk-cancel/tests/test_state_5.py)</summary>

```python
"""Bulk-cancel must only cancel and restore stock for orders owned by the requesting user."""
import app.store as store


def test_bulk_cancel_mixed_owners_only_affects_own_orders(alice_client, bob_client):
    initial_p1 = store.products["p1"].stock
    initial_p2 = store.products["p2"].stock

    # Alice creates an order on p1
    r1 = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 5}]})
    assert r1.status_code == 201
    alice_oid = r1.json()["id"]

    # Bob creates an order on p2
    r2 = bob_client.post("/orders", json={"items": [{"product_id": "p2", "qty": 3}]})
    assert r2.status_code == 201
    bob_oid = r2.json()["id"]

    # Alice bulk-cancels both her own and Bob's order
    r3 = alice_client.post("/orders/bulk-cancel", json={"order_ids": [alice_oid, bob_oid]})
    assert r3.status_code == 200

    # Only Alice's order should be cancelled
    r4 = alice_client.get(f"/orders/{alice_oid}")
    assert r4.status_code == 200
    assert r4.json()["status"] == "cancelled"

    # Bob's order must remain placed
    r5 = bob_client.get(f"/orders/{bob_oid}")
    assert r5.status_code == 200
    assert r5.json()["status"] == "placed"

    # p1 stock restored (Alice's order cancelled), p2 stock NOT restored (Bob's order not cancelled)
    assert store.products["p1"].stock == initial_p1
    assert store.products["p2"].stock == initial_p2 - 3
```

</details>


### F-017 · spec — Only the user who created an order may cancel it; bulk cancel must not cancel orders belonging to other users.

- **Basis:** `spec/orders.md#R7` — "Only the user who created an order may read, modify, or cancel it."
- **Red → green:** fails on PR 3/3 → passes after fix 3/3
- **Fix commit:** `4e542ed` (same root cause as F-001)

<details><summary>Proof test (runs/pr-3-bulk-cancel/tests/test_spec_2.py)</summary>

```python
"""Bulk cancel must not cancel an order owned by a different user (R7, R8)."""
from __future__ import annotations

import app.store as store


def test_bulk_cancel_cannot_cancel_other_users_order(alice_client, bob_client):
    # Alice places an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    alice_order_id = resp.json()["id"]

    # Bob attempts to bulk-cancel Alice's order
    bob_client.post("/orders/bulk-cancel", json={"order_ids": [alice_order_id]})

    # Alice's order must still be in 'placed' status — Bob must not have cancelled it
    assert store.orders[alice_order_id].status == "placed"
```

</details>


## Noise rejected (10)

<details><summary>Show rejected findings</summary>

**does not fail on PR** (10)

- F-005 · edge · `no_5xx` — Sending order_ids as a non-list value must not produce a 5xx server error.
- F-007 · security · `no_5xx` — Calling POST /orders/bulk-cancel without an X-User-Id header must return 401 or 422, never 2xx or 500.
- F-008 · security · `spec/orders.md#R7` — Calling POST /orders/bulk-cancel with an unknown user ID must return 401.
- F-010 · security · `no_unhandled_exception` — A bulk-cancel request with a header injection user ID must not return 500 or expose a stack trace.
- F-013 · state · `no_double_effect` — Calling bulk-cancel twice with the same order IDs must not restore stock more than once.
- F-014 · state · `spec/orders.md#R28` — A delivered order included in a bulk-cancel request must be silently skipped and its stock must not be restored.
- F-016 · spec · `spec/orders.md#R26` — POST /orders/bulk-cancel must return 400 when the order_ids list is empty.
- F-018 · spec · `spec/orders.md#R27` — Stock is restored only for orders that were actually cancelled by the bulk-cancel request, not for skipped orders.
- F-019 · spec · `spec/orders.md#R28` — Orders that are not in placed status are silently skipped during bulk cancel and appear in the skipped list.
- F-020 · spec · `spec/orders.md#R25` — POST /orders/bulk-cancel cancels each eligible placed order and restores the stock of each cancelled order's items.

</details>