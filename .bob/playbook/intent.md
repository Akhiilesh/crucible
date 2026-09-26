# intent.md — Intent reader

## Input

Given a PR branch `<pr>`:

1. Run `git diff main...<pr> -- demo-app/app` and note every added or changed endpoint and function.
2. Read the ticket whose `**Branch:** <pr>` line matches: `demo-app/spec/tickets/`.
3. Read `demo-app/spec/orders.md` (all rules).

## Output

Write `runs/<pr>/intent.json`: a JSON array. Each element covers one spec rule that applies
to the diff.

```json
[
  {
    "behaviour": "one plain English sentence describing what the spec requires",
    "rule_id": "R16",
    "endpoints": ["POST /orders/{order_id}/refund"]
  }
]
```

## Which rules to include

Include **both** of the following:

**A. Feature rules** — rules that directly govern the new or changed endpoints listed in the
   ticket (e.g. the rules cited in the ticket's "Refs:" line).

**B. Cross-cutting rules** — rules that apply to every endpoint in the service and that the
   new endpoints must also obey:
   - Ownership and access rules: any rule requiring that only the resource owner may act on it,
     and that accessing another user's resource returns 403.
   - Any rule governing a field or total that the new endpoint reads or modifies
     (e.g. if the endpoint changes a monetary total, include the rule that the total must
     not go negative).

Do not include rules for endpoints that the diff does not touch.

## Field rules

- `rule_id` must be an ID that exists verbatim in `demo-app/spec/orders.md` (e.g. `R15`, `R16`).
- `behaviour` describes what the spec requires, not what the code does. Never say the code is
  correct or incorrect.
- `endpoints` is a list of HTTP method + path strings exactly as they appear in the route
  decorator, e.g. `"POST /orders/{order_id}/refund"`.
- One entry per rule. If a rule applies to multiple endpoints, list all of them.
- Write the file with `json.dumps(intent, indent=2)` or equivalent. Create parent dirs if needed.
