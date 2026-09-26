# fixer.md — Fixer agent

## Input

`runs/<pr>/verdicts.json` — read only entries where `"verdict": "PROVEN"`.
`<repo_root>` is the directory that contains `.git/`.

## Step 1 — Set up a fix worktree

```
git worktree add runs/<pr>/worktrees/fix <pr>
```

All edits, test runs, and commits happen inside this worktree. Never check out `<pr>` in the
main working tree.

## Step 2 — Fix each PROVEN finding (max 3 attempts per finding)

Work through the PROVEN findings one at a time.

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

## Invariants

- Every commit on `<pr>` must leave the full test suite green.
- Never edit proof tests (anything under `demo-app/tests/crucible/` or `runs/<pr>/tests/`).
- Never edit `demo-app/spec/`, `demo-app/spec/tickets/`, or any playbook file.
- Each fix commit touches `demo-app/app/` and `demo-app/tests/crucible/` only.
