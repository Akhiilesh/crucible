# fixer.md — Fixer agent

## Input

`runs/<pr>/verdicts.json` — read only the entries where `"verdict": "PROVEN"`.

## Step 1 — Commit proof tests (once, before any fix)

1. Check out branch `<pr>`.
2. For each PROVEN finding, copy `test_path` (relative to repo root) into
   `demo-app/tests/crucible/`. Create `demo-app/tests/crucible/__init__.py` if it does not exist.
3. Commit: `"test(<pr>): add crucible proof tests"`.
4. These files are now read-only. Never edit them again.

## Step 2 — Fix each PROVEN finding

For each PROVEN finding in order:

1. Read the proof test to understand what behaviour it asserts.
2. Make the minimal change to `demo-app/app/` only that makes the test pass.
   Do not edit spec files, ticket files, or any test file.
3. Run `.venv/bin/python -m pytest demo-app/tests -q`.
4. If green: commit `"fix(<id>): <claim>"` and record the short commit SHA as `fix_commit`
   in `runs/<pr>/verdicts.json` for this finding.
5. If not green after this attempt:
   - Revert the change (`git checkout -- demo-app/app/`).
   - Try a different approach (up to 3 attempts total per finding).
   - After 3 failed attempts: leave the verdict as `"UNFIXED"`, set `fix_commit` to null,
     and move on to the next finding.

## Step 3 — Return to main

After all findings are processed, run `git checkout main`. Update `runs/<pr>/verdicts.json`
with the final `fix_commit` values.

## Invariants

- Never edit proof tests (anything in `demo-app/tests/crucible/` or `runs/<pr>/tests/`).
- Never edit `demo-app/spec/` or `demo-app/spec/tickets/`.
- Each fix commit touches `demo-app/app/` only.
- If the full test suite was green before you started, it must remain green after each fix.
