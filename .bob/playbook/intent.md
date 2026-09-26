# intent.md — Intent reader

## Input

Given a PR branch `<pr>`:

1. Run `git diff main...<pr> -- demo-app/app` and note every added endpoint and function.
2. Read the ticket whose `**Branch:** <pr>` line matches: `demo-app/spec/tickets/`.
3. Read `demo-app/spec/orders.md` (all rules).

## Output

Write `runs/<pr>/intent.json`: a JSON array. Each element covers one spec rule that is relevant to the diff.

```json
[
  {
    "behaviour": "one plain English sentence describing what the spec requires",
    "rule_id": "R16",
    "endpoints": ["POST /orders/{order_id}/refund"]
  }
]
```

## Rules

- Include only rules that are directly exercised by the added or changed endpoints in the diff.
  Do not include rules for endpoints that were not touched by the PR.
- `rule_id` must be an ID that exists verbatim in `demo-app/spec/orders.md` (e.g. `R15`, `R16`).
- `behaviour` describes what the spec requires, not what the code does. Never say the code is
  correct or incorrect.
- `endpoints` is a list of HTTP method + path strings exactly as they appear in the route
  decorator, e.g. `"POST /orders/{order_id}/refund"`.
- One entry per rule. If a rule applies to multiple endpoints, list all of them.
- Write the file with `json.dumps(intent, indent=2)` or equivalent. Create parent dirs if needed.
