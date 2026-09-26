# fixer.md — Fixer agent

## Input

`runs/<pr>/verdicts.json` — read only entries where `"verdict": "PROVEN"`.
`<repo_root>` is the directory that contains `.git/`.

## Step 1 — Set up a fix worktree

Record the start time: `date -u +%Y-%m-%dT%H:%M:%SZ`.

```
git worktree add runs/<pr>/worktrees/fix <pr>
```

All edits, test runs, and commits happen inside this worktree. Never check out `<pr>` in the
main working tree.

## Step 2 — Fix each PROVEN finding (max 3 attempts per finding)

Work through the PROVEN findings one at a time, in id order.

**Already fixed?** First copy the finding's proof test into `<worktree>/demo-app/tests/crucible/`
and run the suite. If the proof test already passes (an earlier fix in this run covered the same
root cause), commit only the proof test as `test(<id>): proof test, fixed by <earlier sha>`, set
`fix_commit` to that earlier SHA, and move on. Do not change app code for it.

**Per attempt:**

1. Copy the finding's `test_path` (relative to repo root) into
   `<worktree>/demo-app/tests/crucible/`. Create `__init__.py` in that directory if absent.
2. Make the minimal change to `<worktree>/demo-app/app/` only.
3. Run from the worktree root:
   ```
   <repo_root>/.venv/bin/python -m pytest demo-app/tests -q
   ```
4. **If green**: commit the proof test and the fix together:
   ```
   git -C <worktree> add demo-app/
   git -C <worktree> commit -m "fix(<id>): <claim>"
   ```
   Record the short SHA (`git -C <worktree> rev-parse --short HEAD`) as `fix_commit`.
   Move on to the next finding.

5. **If still red after 3 attempts**:
   - Discard all uncommitted changes in the worktree:
     ```
     git -C <worktree> checkout -- .
     git -C <worktree> clean -fd demo-app/
     ```
   - Set `verdict` to `"UNFIXED"`, `fix_commit` to `null`. Do not commit the proof test.
   - Move on to the next finding.

## Step 3 — Finish

1. Update `runs/<pr>/verdicts.json` in the **main working tree** with the final `fix_commit`
   values and any `UNFIXED` verdicts.
2. Remove the worktree:
   ```
   git worktree remove runs/<pr>/worktrees/fix
   ```
3. Record the end time and add `"fix": {"start", "end", "seconds", "by": "<agent name>"}` to
   `runs/<pr>/timing.json`.
4. Confirm the fixes with the verifier (every fixed proof test must pass 3/3 on `<pr>`), then build
   the report:
   ```
   .venv/bin/python -m crucible.cli verify --pr <pr> --run-dir runs/<pr> --after-fix
   .venv/bin/python -m crucible.cli report --run-dir runs/<pr>
   ```

## Invariants

- Every commit on `<pr>` must leave the full test suite green.
- Never edit proof tests (anything under `demo-app/tests/crucible/` or `runs/<pr>/tests/`).
- Never edit `demo-app/spec/`, `demo-app/spec/tickets/`, or any playbook file.
- Each fix commit touches `demo-app/app/` and `demo-app/tests/crucible/` only.
