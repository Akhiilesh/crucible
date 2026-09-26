# attack-common.md — Rules for every attacker

These rules apply to all four lens agents. Read your lens file for what to look for.

## What you may read

- `.bob/playbook/` — all playbook files
- `runs/<pr>/intent.json` — the intent produced for this PR
- `demo-app/` as it exists on `main` (app code, tests, spec, tickets)
- PR changes via `git diff main...<pr>` and `git show <pr>:<path>`

## What you must never read

- `agent.md`, `Crucible PRD.md`, `crucible-phases-0-2-plan.md`
- `PLANTED_BUGS.md` or any file whose name suggests a bug list
- `bob-sessions/`
- Any `runs/` directory other than `runs/<pr>/intent.json`
- `crucible/` (the verifier source)
- Any file outside the repository

## What you must never run

- `git checkout`, `git switch`, `git stash`, `git commit`, `git merge`
- Any command that modifies the working tree or git history
- Attackers share one working tree and run in parallel; do not change it

## Output

For each finding, write two things:

**1. A test file** at `runs/<pr>/tests/test_<lens>_<n>.py` (n = 1..5, no leading zeros).

Test file requirements:
- Exactly one test function per file.
- Use the `alice_client` or `bob_client` fixtures. They are already configured with
  `raise_server_exceptions=False` and the store resets automatically before each test.
- Assert the **correct** behaviour described by the spec or universal property, so the test
  fails only when the bug is present and passes when the code is correct.
- All failures must be plain `assert` statements, not `pytest.raises` or manual raises.
- Never let the test crash before the assertion:
  - Check the status code before calling `.json()` or indexing the response body.
  - Import only modules that exist on main: `app.store`, `app.main`, `app.models`,
    `datetime`, `json`, standard library only.
  - For `app.store` direct access, use `store.orders[oid].model_copy(update={...})`.
- Write URL paths as literal strings or simple f-strings only, e.g.
  `f"/orders/{oid}/refund"`. Do not build URLs by concatenation or helper functions.
- To test time-dependent behaviour, backdate a timestamp by editing the store directly:
  ```python
  store.orders[oid] = store.orders[oid].model_copy(update={"delivered_at": past_dt})
  ```
  Do not import or use any time-mocking library.
- No comments or docstrings that mention branch names or planted bugs.
  Describe the expected behaviour only.

**2. An entry in** `runs/<pr>/findings/<lens>.json` (append to the list, or create it):

```json
{
  "id": "<LENS>-<n>",
  "lens": "<lens>",
  "claim": "one plain English sentence stating the expected behaviour",
  "basis": "spec/orders.md#R16",
  "test_path": "runs/<pr>/tests/test_<lens>_<n>.py"
}
```

- `id` format: lens name in uppercase, hyphen, number — e.g. `SPEC-1`, `EDGE-3`.
- `basis` must be either `"spec/orders.md#R<n>"` where `R<n>:` exists in
  `demo-app/spec/orders.md`, or one of the universal properties:
  `no_5xx`, `no_unhandled_exception`, `no_data_leak`, `no_negative_money`, `no_double_effect`.
- `claim` is one plain English sentence. Do not mention branches or bugs.
- `test_path` is relative to the repository root.

## Limits

- Maximum 5 findings per lens. Choose the highest-value ones.
- No style, naming, performance or documentation comments.
- Quality over quantity: a finding that will fail the verifier wastes a slot.
