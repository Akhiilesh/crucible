# Crucible report — `pr-1-refunds`

**2 proven** · **18 rejected** · 2 fixed · 0 unfixed · reviewed in **1m 35s**

## Scorecard

| Metric | Value |
|---|---|
| Raw suspicions (attacker findings) | 20 |
| Proven by failing test (all 4 gates) | 2 |
| Unique bugs (distinct fixes) | 1 |
| Rejected as noise | 18 |
| Fixed (proof test now passes 3/3) | 2 |
| Unfixed | 0 |
| Precision of reported findings | 100% (2 of 2 carry a failing proof test) |
| Suspicions confirmed | 10% (2 of 20) |
| Full suite after fixes | green — 31 passed, 1 warning in 0.08s (`0804c3e`) |

### Time per stage

| Stage | Seconds | By |
|---|---|---|
| attack | 46 | bob-subagents |
| verify | 46 | crucible-cli |
| fix | 1 | claude-code |
| verify_after_fix | 2 | crucible-cli |
| **total** | **95** | |

Attack mode: **parallel** (4 lenses).

## Proven findings

### F-014 · state — The 14-day refund window is counted from delivered_at; a request more than 14 days after delivered_at must return 400 even if created_at is recent.

- **Basis:** `spec/orders.md#R16` — "The refund window is 14 days counted from delivered_at, not created_at."
- **Red → green:** fails on PR 3/3 → passes after fix 3/3
- **Fix commit:** `14f2146`

<details><summary>Proof test (runs/pr-1-refunds/tests/test_state_4.py)</summary>

```python
"""A refund request more than 14 days after delivered_at must return 400."""
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

import app.store as store


def test_refund_outside_window_from_delivered_at_rejected(alice_client: TestClient) -> None:
    """The 14-day refund window is counted from delivered_at; a request 15 days after
    delivered_at must return 400 even if the order was created recently."""
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    alice_client.post(f"/orders/{oid}/deliver")

    # Backdate delivered_at to 15 days ago, keep created_at recent
    now = datetime.now(tz=timezone.utc)
    store.orders[oid] = store.orders[oid].model_copy(update={
        "delivered_at": now - timedelta(days=15),
        "created_at": now - timedelta(days=1),
    })

    r = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 100})
    assert r.status_code == 400
```

</details>

```diff
diff --git a/demo-app/app/main.py b/demo-app/app/main.py
index 6522393..a209c66 100644
--- a/demo-app/app/main.py
+++ b/demo-app/app/main.py
@@ -132,7 +132,7 @@ def refund_order(
     if order.status != OrderStatus.delivered:
         raise HTTPException(status_code=400, detail="Only delivered orders can be refunded")
 
-    window_start = order.created_at
+    window_start = order.delivered_at
     if datetime.now(tz=timezone.utc) - window_start > timedelta(days=14):
         raise HTTPException(status_code=400, detail="Refund window has expired")
```

### F-016 · spec — The 14-day refund window is counted from delivered_at; an order delivered 2 days ago but created 20 days ago must still be refundable.

- **Basis:** `spec/orders.md#R16` — "The refund window is 14 days counted from delivered_at, not created_at."
- **Red → green:** fails on PR 3/3 → passes after fix 3/3
- **Fix commit:** `14f2146` (same root cause as F-014)

<details><summary>Proof test (runs/pr-1-refunds/tests/test_spec_1.py)</summary>

```python
"""R16: The 14-day refund window is counted from delivered_at, not created_at."""
import pytest
from datetime import datetime, timedelta, timezone
import app.store as store


def test_refund_window_counted_from_delivered_at(alice_client):
    # Create and deliver an order
    resp = alice_client.post("/orders", json={"items": [{"product_id": "p1", "qty": 1}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]

    deliver_resp = alice_client.post(f"/orders/{oid}/deliver")
    assert deliver_resp.status_code == 200

    # Backdate created_at to 20 days ago but delivered_at to 2 days ago.
    # Per R16, the window starts at delivered_at (2 days ago), so refund must be allowed.
    now = datetime.now(tz=timezone.utc)
    store.orders[oid] = store.orders[oid].model_copy(update={
        "created_at": now - timedelta(days=20),
        "delivered_at": now - timedelta(days=2),
    })

    resp = alice_client.post(f"/orders/{oid}/refund", json={"amount_paise": 500})
    assert resp.status_code == 200
```

</details>


## Noise rejected (18)

<details><summary>Show rejected findings</summary>

**does not fail on PR** (18)

- F-001 · edge · `spec/orders.md#R18` — A refund request with amount_paise equal to 0 must return 400.
- F-002 · edge · `spec/orders.md#R18` — A refund request with amount_paise greater than the order total must return 400.
- F-003 · edge · `spec/orders.md#R16` — A refund request made within 14 days of delivered_at must succeed with status 200.
- F-004 · edge · `spec/orders.md#R15` — A refund request for a non-existent order ID must return 404.
- F-005 · edge · `spec/orders.md#R18` — A refund request with a negative amount_paise must return 400.
- F-006 · security · `spec/orders.md#R8` — A user cannot refund an order belonging to another user; the request must return 403.
- F-007 · security · `no_5xx` — A refund request with no X-User-Id header must return 401 or 422, never a successful response.
- F-008 · security · `spec/orders.md#R7` — A refund request from an unknown user must return 401.
- F-009 · security · `no_data_leak` — A 403 error response on the refund endpoint must not expose the target order's internal data.
- F-010 · security · `spec/orders.md#R7` — A user cannot change the status of another user's order by calling the refund endpoint.
- F-011 · state · `spec/orders.md#R19` — A refunded order cannot be refunded again; the second refund request must return 400.
- F-012 · state · `spec/orders.md#R15` — Refunds are only allowed for delivered orders; attempting to refund a placed order must return 400.
- F-013 · state · `spec/orders.md#R15` — Refunds are only allowed for delivered orders; attempting to refund a cancelled order must return 400.
- F-015 · state · `spec/orders.md#R20` — A successful refund sets the order status to 'refunded' and records the refunded amount.
- F-017 · spec · `spec/orders.md#R15` — Refunds are only allowed for orders with status 'delivered'; a placed order must receive 400.
- F-018 · spec · `spec/orders.md#R18` — A refund amount greater than the order total must return 400.
- F-019 · spec · `spec/orders.md#R19` — A refunded order cannot be refunded again; a second refund request must return 400.
- F-020 · spec · `spec/orders.md#R20` — A successful refund returns 200 and sets the order status to 'refunded'.

</details>