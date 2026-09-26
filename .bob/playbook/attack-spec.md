# attack-spec.md — Spec-violation attacker lens

Read `attack-common.md` first. This file adds lens-specific direction.

## What to look for

Work through `runs/<pr>/intent.json` entry by entry. For each `{behaviour, rule_id, endpoints}`:

1. State what the spec requires (the `behaviour` field tells you).
2. Design a test that will fail if the implementation violates that requirement.
3. Write the test and the finding.

Consider every entry in intent.json. If there are more entries than the 5-finding limit in
`attack-common.md`, keep the tests most likely to expose a real violation. If you cannot write a
meaningful test for a rule, note it and move to the next.

## Approach

- For each rule, think: "what input would expose a violation?" Then write that input as the test.
- Cite the exact `rule_id` from intent.json as the `basis` (format: `spec/orders.md#R<n>`).
- The `claim` should echo the `behaviour` from intent.json, phrased as what the spec requires.

## Output

`runs/<pr>/findings/spec.json` and test files `runs/<pr>/tests/test_spec_<n>.py`.
Follow all rules in `attack-common.md`.
