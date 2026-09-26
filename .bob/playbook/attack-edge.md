# attack-edge.md — Edge-case attacker lens

Read `attack-common.md` first. This file adds lens-specific direction.

## What to look for

Probe the new endpoints with values at and beyond their documented limits:

- **Zero and negative numbers**: numeric fields set to 0 or -1.
- **Off-by-one on documented limits**: values exactly at the boundary, one below, and one above.
- **Empty and missing fields**: omit required JSON fields entirely; send an empty body `{}`.
- **Wrong types**: send a string where an int is expected, a float, null.
- **Huge values**: integers far beyond any realistic business value (e.g. 2^31).
- **Unknown IDs**: resource IDs that do not exist in the store.
- **Empty collections**: empty lists or arrays where the spec requires at least one element.

## Output

`runs/<pr>/findings/edge.json` and test files `runs/<pr>/tests/test_edge_<n>.py`.
Follow all rules in `attack-common.md`.
