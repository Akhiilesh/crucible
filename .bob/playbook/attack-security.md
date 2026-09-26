# attack-security.md — Security attacker lens

Read `attack-common.md` first. This file adds lens-specific direction.

## What to look for

- **Cross-user access (IDOR)**: send requests for one user's resources using a different user's
  `X-User-Id` header. Expect 403 on every new endpoint.
- **Missing or unknown user header**: omit the `X-User-Id` header entirely; send an unknown value.
  Expect 401 or 422, never a 500 or a successful response.
- **Header injection**: send a user id containing special characters (spaces, slashes, nulls).
  The response must not reveal internal state or a stack trace.
- **Information leaks in error bodies**: when a request fails (400, 403, 404), the response body
  must not expose internal state, stack traces, or data belonging to another user.
- **Privilege escalation**: a user must not be able to trigger state changes on another user's
  resources even if they know the resource id.

## Output

`runs/<pr>/findings/security.json` and test files `runs/<pr>/tests/test_security_<n>.py`.
Follow all rules in `attack-common.md`.
