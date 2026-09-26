# attack-state.md — State and consistency attacker lens

Read `attack-common.md` first. This file adds lens-specific direction.

## What to look for

- **Double effects**: call the same state-changing endpoint twice on the same resource. The
  second call must be rejected or be a no-op — it must not apply the operation twice.
- **Forbidden state transitions**: attempt an operation on a resource in a state the spec
  forbids. Check every status transition the spec does not permit.
- **Ordering**: try operations out of the expected sequence (e.g. skip a prerequisite step).
- **Numeric consistency**: after a state-changing operation, verify that totals, counts and
  balances are consistent with what the spec promises.
- **Independence**: place multiple resources and operate on them in different orders to confirm
  that each resource's state is tracked independently.

## Output

`runs/<pr>/findings/state.json` and test files `runs/<pr>/tests/test_state_<n>.py`.
Follow all rules in `attack-common.md`.
