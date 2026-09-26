# attack-edge.md — Edge-case attacker lens

Read `attack-common.md` first. This file adds lens-specific direction.

## What to look for

Probe the new endpoints with values at and beyond their documented limits:

- **Zero and negative numbers**: amount_paise = 0, amount_paise = -1, qty = 0, percent = 0.
- **Off-by-one on limits**: amount_paise exactly equal to order total; amount_paise = total + 1;
  refund exactly at day 14 vs day 15 (by manipulating delivered_at in the store).
- **Empty and missing fields**: omit required JSON fields entirely; send an empty body `{}`.
- **Wrong types**: send a string where an int is expected, a float, null.
- **Huge values**: amount_paise larger than any realistic order total (e.g. 2^31).
- **Unknown IDs**: order_id that does not exist in the store.

## Focus

For `pr-1-refunds`: concentrate on the refund amount limits (R18) and the 14-day window
boundary (R16, R17). Off-by-one errors and boundary values are the most likely edge bugs.

## Output

`runs/<pr>/findings/edge.json` and test files `runs/<pr>/tests/test_edge_<n>.py`.
Follow all rules in `attack-common.md`.
