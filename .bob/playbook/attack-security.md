# attack-security.md — Security attacker lens

Read `attack-common.md` first. This file adds lens-specific direction.

## What to look for

- **Cross-user access (IDOR)**: send requests for Alice's orders using Bob's `X-User-Id` header.
  Expect 403. Check every new endpoint.
- **Missing or unknown user header**: omit the `X-User-Id` header entirely; send an unknown value.
  Expect 401 or 422, not a 500 or a successful response.
- **Header injection**: send a user id that contains special characters (spaces, slashes, nulls).
  The response must not reveal internal details.
- **Information leaks in error bodies**: when a request fails (400, 403, 404), the response body
  must not expose internal state, stack traces, or another user's data.
- **Privilege escalation**: a user must not be able to trigger state changes (refund, cancel) on
  another user's order even if they know the order id.

## Focus

For `pr-1-refunds`: verify that the refund endpoint enforces ownership (R7, R8) and that error
responses for invalid requests do not leak order details belonging to other users.

## Output

`runs/<pr>/findings/security.json` and test files `runs/<pr>/tests/test_security_<n>.py`.
Follow all rules in `attack-common.md`.
