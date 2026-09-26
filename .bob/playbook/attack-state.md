# attack-state.md — State and consistency attacker lens

Read `attack-common.md` first. This file adds lens-specific direction.

## What to look for

- **Double effects**: call the same endpoint twice on the same order. The second call must be
  rejected or idempotent — it must not apply the operation twice.
- **Forbidden state transitions**: attempt an operation on an order in a state the spec forbids.
  Refund a placed order; refund a cancelled order; refund an already-refunded order (R15, R19).
- **Ordering**: deliver then refund; place then immediately refund without delivering.
- **Stock and money consistency**: after a refund, verify the order total and status are
  consistent with what the spec promises. A refund must not alter stock (only cancellation does).
- **Concurrent-style sequences**: place multiple orders and operate on them in different orders
  to check that each order's state is independent.

## Focus

For `pr-1-refunds`: double-refund (R19) and refunding non-delivered orders (R15) are the
primary targets. Also check that a refunded order's status is "refunded" (R20) and that
the refunded_paise field reflects the requested amount.

## Output

`runs/<pr>/findings/state.json` and test files `runs/<pr>/tests/test_state_<n>.py`.
Follow all rules in `attack-common.md`.
