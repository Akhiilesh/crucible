# Crucible — Build Plan: Phases 0–2

**Scope:** Project skeleton, demo app, and the verifier — the "never cut" core.  
**Source of truth:** `agent.md` (build instructions) and `Crucible PRD.md` (architecture + contracts).  
**Approach:** readable, reusable Python; minimal complexity; strict data contracts between components.

---

## Architecture recap

```
Phase 0: repo skeleton + CLI scaffold
Phase 1: demo-app (FastAPI orders service) + spec + 3 feature branches
Phase 2: crucible/verify.py + crucible/gates.py (the proof-gate engine)
```

The Python CLI (`crucible/`) is entirely deterministic. Bob does the thinking; the CLI does the judging.

---

## Sub-Task 1 — Project skeleton (Phase 0)

**Intent**  
Create the repo structure, install tooling, and confirm the Typer CLI boots. Nothing functional yet — just the foundation every other sub-task builds on.

**Expected Outcomes**
- `python -m crucible.cli --help` prints the help message with `verify` and `report` as placeholder commands.
- `pyproject.toml` lists all required deps (fastapi, uvicorn, pytest, httpx, typer, jinja2, pydantic).
- Git repo initialised with a clean first commit `chore: project skeleton`.

**Todo List**
1. Create `pyproject.toml` with `[project]` metadata, deps, and a `[project.scripts]` entry for `crucible`.
2. Create `crucible/__init__.py` (empty).
3. Create `crucible/cli.py` — Typer app with two placeholder commands: `verify` and `report`, each printing "not implemented yet".
4. Create `.bob/playbook/` directory (empty, populated in Phase 3).
5. Create `demo-app/` directory (populated in Phase 1).
6. Create `runs/.gitkeep` and `bob-sessions/.gitkeep`.
7. Create `README.md` — title line + one sentence describing the project.
8. Create `.gitignore` — Python defaults plus `runs/*/worktrees/`.
9. `git init`, `git add -A`, `git commit -m "chore: project skeleton"`.
10. Run `python -m crucible.cli --help` and confirm it prints.

**Relevant Context**
- `agent.md` §PHASE 0 — exact list of files and gate criterion.
- Typer docs pattern: `app = typer.Typer()`, `@app.command()`, `if __name__ == "__main__": app()`.
- The CLI module is invoked as `python -m crucible.cli`, so `crucible/cli.py` must have a `if __name__ == "__main__"` guard.

**Status:** `[ ] pending`

---

## Sub-Task 2 — Base service on `main` (Phase 1, Step 1.1)

**Intent**  
Build the FastAPI "orders and refunds" service in `demo-app/` with an in-memory store. This is the codebase the verifier will later test. It must be correct — no planted bugs yet.

**Expected Outcomes**
- `demo-app/app/main.py` — FastAPI app with all 4 endpoints.
- `demo-app/app/models.py` — Pydantic models for `User`, `Product`, `Order`.
- `demo-app/app/store.py` — in-memory dict-based store with a `reset()` function.
- `demo-app/tests/conftest.py` — pytest fixture that resets the store between tests.
- `demo-app/tests/test_orders.py` — at least 15 passing tests using `TestClient`.
- All tests pass on `main`.
- Commit `feat: demo orders service`.

**Todo List**
1. Create `demo-app/app/__init__.py`.
2. Create `demo-app/app/models.py` — define `User`, `Product`, `Order` as Pydantic `BaseModel` subclasses, plus an `OrderStatus` `str`-enum (`placed | delivered | cancelled | refunded`).
3. Create `demo-app/app/store.py` — module-level dicts for users, products, orders; a `reset()` function that restores fixture data; a small seed of 2 users and 3 products.
4. Create `demo-app/app/main.py` — FastAPI app; import store; implement `POST /orders`, `GET /orders/{id}`, `POST /orders/{id}/deliver`, `POST /orders/{id}/cancel`. Enforce `X-User-Id` header; return 403 if a user accesses another user's order; return 404 if resource not found; return 400 for invalid transitions.
5. Create `demo-app/tests/__init__.py`.
6. Create `demo-app/tests/conftest.py` — `@pytest.fixture(autouse=True)` that calls `store.reset()` before each test; a `client` fixture returning `TestClient(app)`.
7. Create `demo-app/tests/test_orders.py` — cover: create order (happy path, stock reduced, total computed), get own order, 403 on other user's order, deliver, cancel placed order, 400 on cancel delivered order, 404 on missing id, multiple items in one order, stock not reduced on failed create, etc. — minimum 15 tests.
8. Run `pytest demo-app/tests/ -v` and confirm all pass.
9. `git add -A && git commit -m "feat: demo orders service"`.

**Relevant Context**
- `agent.md` §PHASE 1, Step 1.1 — exact models, endpoint list, header auth requirement.
- `store.py` reset pattern is critical — the verifier later relies on fresh state per test run.
- `total_paise` is computed from product prices × quantities; `stock` is decremented on order creation and restored on cancel.
- Status transitions: `placed → delivered`, `placed → cancelled`. `delivered` and `cancelled` orders cannot transition further (until refund is added in the feature branch).

---

## Sub-Task 3 — Spec and ticket documents (Phase 1, Step 1.2)

**Intent**  
Write the numbered spec rules and per-PR ticket stubs that Bob (and the verifier's G4 grounding gate) will reference. These are static documents; correctness of rule IDs matters because the verifier validates `basis` fields against them.

**Expected Outcomes**
- `demo-app/spec/orders.md` — all base rules (R1–Rn) for the existing service plus appended rules for refunds, discounts, and bulk-cancel, each on its own line as `R<n>: ...`.
- `demo-app/spec/tickets/PR-1-refunds.md`, `PR-2-discounts.md`, `PR-3-bulk-cancel.md` — 4–6 lines each, Jira-style, citing rule IDs.
- Commit to `main`.

**Todo List**
1. Create `demo-app/spec/orders.md`:
   - Base section: rules for order creation (stock check, total computation), ownership enforcement, status transitions, deliver and cancel semantics.
   - Refund section: delivered-only, 14-day window from `delivered_at`, amount > 0 and ≤ total, no double refund.
   - Discount section: 1–50% off, owner-only, total ≥ 0.
   - Bulk-cancel section: `POST /orders/bulk-cancel`, 400 on empty list, stock restored only for actually-cancelled orders.
   - Number rules sequentially from R1. Keep each rule to one plain English line.
2. Create `demo-app/spec/tickets/PR-1-refunds.md` — title, summary, rule refs (refund rules only).
3. Create `demo-app/spec/tickets/PR-2-discounts.md` — title, summary, rule refs (discount rules only).
4. Create `demo-app/spec/tickets/PR-3-bulk-cancel.md` — title, summary, rule refs (bulk-cancel rules only).
5. `git add -A && git commit -m "docs: spec rules and PR tickets"`.

**Relevant Context**
- `agent.md` §PHASE 1, Step 1.2 — exact list of rules to encode.
- Rule IDs must be stable; the verifier's G4 gate reads `demo-app/spec/orders.md` and checks that the `basis` field in a finding matches an existing rule ID.
- Grounding check format: `spec/orders.md#R<n>`. The verifier must parse this pattern.

---

## Sub-Task 4 — Feature branches with planted bugs (Phase 1, Step 1.3)

**Intent**  
Create three feature branches, each implementing the new feature described by its ticket, but with bugs planted by the human. The human pastes the bug instructions in chat; this sub-task implements exactly what is said, without writing bug descriptions into any file.

**Expected Outcomes**
- Branch `pr-1-refunds`: refund endpoint implemented, feature tests pass, bugs present but not commented.
- Branch `pr-2-discounts`: discount endpoint implemented, feature tests pass, bugs present.
- Branch `pr-3-bulk-cancel`: bulk-cancel endpoint implemented, feature tests pass, bugs present.
- `git branch` shows all 4 branches (`main` + 3 feature branches).
- All three feature test suites are green.

**Todo List**
1. **WAIT** — human pastes planted-bug instructions for `pr-1-refunds` in chat.
2. Check out branch `pr-1-refunds` from `main`.
3. Implement the refund endpoint (`POST /orders/{id}/refund`) per the ticket and the planted-bug instructions. Add feature tests in `demo-app/tests/test_refunds.py` that pass (they test happy paths, not the bugs).
4. Run `pytest demo-app/tests/ -v` — all must pass.
5. `git add -A && git commit -m "feat(pr-1): refund endpoint"`.
6. Repeat steps 1–5 for `pr-2-discounts` (discount endpoint, `POST /orders/{id}/discount`).
7. Repeat steps 1–5 for `pr-3-bulk-cancel` (bulk cancel endpoint, `POST /orders/bulk-cancel`).
8. Return to `main`. Run `git branch` to confirm all 4 branches exist.

**Relevant Context**
- `agent.md` rule 5: never write planted bug descriptions to any file in the repo.
- `agent.md` rule 6: attacker subagents must not read `agent.md`. Bugs must not be documented in code comments either.
- Feature tests are separate from proof tests — they test the happy path and must stay green.

---

## Sub-Task 5 — Verifier core: `verify.py` and `gates.py` (Phase 2, Steps 2.1–2.2)

**Intent**  
Implement the deterministic heart of Crucible. The verifier is what makes Crucible trustworthy — it applies four mechanical gates and never lets the AI grade its own work. This must be correct and auditable.

**Expected Outcomes**
- `crucible/verify.py` — orchestrates the full verification flow for a single run directory.
- `crucible/gates.py` — four gate functions (G1–G4), each pure and independently testable.
- `crucible/cli.py` — `verify` command wired up: `--pr`, `--base`, `--run-dir`, `--keep` flags.
- `runs/<pr>/verdicts.json` written after a run.
- Terminal prints a summary table: PROVEN / REJECTED counts with reasons.
- Unit tests in `tests/test_verifier.py`.

**Todo List**
1. Create `crucible/gates.py`:
   - `gate_g1_fails_on_pr(junit_path) -> tuple[bool, str]` — parse JUnit XML; return `(True, "")` if `<failure>` present; `(False, "test broken")` if `<error>` present; `(False, "did not fail")` if neither.
   - `gate_g2_blame(junit_base_path, diff_text, test_file_path) -> tuple[bool, str]` — if test passes on base: `(True, "passes_on_base")`; if test fails on base but targeted function/endpoint is in the diff: `(True, "new_code")`; else `(False, "pre-existing behaviour")`.
   - `gate_g3_reproducible(run_fn, n=3) -> tuple[bool, str]` — call `run_fn()` three times independently; return `(True, "3/3")` if all fail; else `(False, "flaky")`.
   - `gate_g4_grounded(basis, spec_path) -> tuple[bool, str]` — if `basis` is a universal property (`no_5xx` etc.), return `(True, "")`; if `basis` matches `spec/orders.md#R<n>`, read the spec file and confirm R<n> exists; else `(False, "ungrounded")`.

2. Create `crucible/verify.py`:
   - `load_findings(findings_path) -> list[dict]` — read `findings.json`.
   - `run_pytest_junit(test_file, worktree_path, junit_out) -> Path` — subprocess call to `pytest <test_file> --junitxml=<junit_out>` with `cwd=<worktree_path>/demo-app`; return junit path.
   - `create_worktrees(pr_branch, base_branch, run_dir) -> tuple[Path, Path]` — `git worktree add` for PR and base into `<run_dir>/worktrees/pr` and `<run_dir>/worktrees/base`; return both paths.
   - `remove_worktrees(run_dir)` — `git worktree remove --force` for both worktrees.
   - `copy_test_to_worktree(test_path, worktree_path)` — copy the proof test into `demo-app/tests/crucible/` inside the worktree.
   - `verify_finding(finding, pr_worktree, base_worktree, spec_path) -> dict` — runs all 4 gates and returns a verdict dict matching the contract in `agent.md §4`.
   - `run_verification(pr_branch, base_branch, run_dir, keep=False)` — top-level function: create worktrees → load findings → verify each → write `verdicts.json` → print summary → optionally remove worktrees.

3. Wire `crucible/cli.py` `verify` command to call `run_verification(...)`.

4. Create `tests/test_verifier.py` — unit tests for:
   - `gate_g1`: JUnit XML with `<failure>` → True; with `<error>` → False, "test broken"; with all-pass → False.
   - `gate_g4`: valid spec rule ID → True; non-existent rule ID → False; universal property → True; garbage → False.
   - `gate_g2`: passing base result → `passes_on_base`; failing base + new code in diff → `new_code`; failing base + old code → `pre-existing behaviour`.
   - `load_findings`: parses a JSON list correctly.
   - Do not test subprocess behaviour in unit tests — test gate logic only with fixture inputs.

5. Run `pytest tests/test_verifier.py -v` — all must pass.

**Relevant Context**
- `agent.md` §5 — exact gate definitions and rejection reasons. Follow these exactly; do not add gates.
- `agent.md` §4 — data contract for `verdicts.json`; every field must be present.
- JUnit XML format: `<testsuite><testcase ...><failure .../></testcase></testsuite>`. Use `xml.etree.ElementTree` (stdlib).
- G2 diff parsing: look for `+def <function>` or `+async def <function>` or `+@app.<method>("/<endpoint>")` in the diff text; extract the name and check if the test file references it.
- G3 reproducibility: each run must be a fresh subprocess (not reusing the same pytest process).
- Universal properties list (from `agent.md §4`): `no_5xx`, `no_unhandled_exception`, `no_data_leak`, `no_negative_money`, `no_double_effect`.

---

## Sub-Task 6 — Self-test run (Phase 2, Step 2.3)

**Intent**  
Validate the verifier against four hand-crafted findings: one real, three deliberately broken in different ways. The expected output is exactly 1 PROVEN and 3 REJECTED with correct reasons. If the verifier produces wrong results, fix the verifier — not the test findings.

**Expected Outcomes**
- `runs/verifier-selftest/findings.json` — 4 findings.
- `runs/verifier-selftest/tests/` — 4 test files.
- `runs/verifier-selftest/verdicts.json` — 1 PROVEN, 3 REJECTED.
- Each REJECTED finding has the correct `reason` field as specified in `agent.md §5`.
- **Gate:** exactly `{"PROVEN": 1, "REJECTED": 3}` with reasons `"ungrounded"`, `"test broken"`, `"pre-existing behaviour"`.

**Todo List**
1. Create `runs/verifier-selftest/tests/test_f001.py` — **Real finding**: calls `POST /orders/{id}/refund` after the 14-day window using `created_at` (not `delivered_at`) and asserts a 400 response; uses `TestClient(app, raise_server_exceptions=False)`.
2. Create `runs/verifier-selftest/tests/test_f002.py` — **Fake wrong expectation**: asserts refunds are allowed for `placed` orders; `basis` cites a non-existent rule ID like `spec/orders.md#R99`.
3. Create `runs/verifier-selftest/tests/test_f003.py` — **Fake broken**: imports `from demo_app.nonexistent import something`; will produce an `<error>` (not `<failure>`) in JUnit output.
4. Create `runs/verifier-selftest/tests/test_f004.py` — **Fake pre-existing**: asserts something that already fails on `main` (e.g., a non-existent endpoint returns 200); unrelated to the `pr-1-refunds` changes.
5. Create `runs/verifier-selftest/findings.json` — 4 entries matching the data contract.
6. Run: `python -m crucible.cli verify --pr pr-1-refunds --base main --run-dir runs/verifier-selftest`.
7. Read `runs/verifier-selftest/verdicts.json` and confirm: 1 PROVEN (F001), F002 = REJECTED `"ungrounded"`, F003 = REJECTED `"test broken"`, F004 = REJECTED `"pre-existing behaviour"`.
8. If any verdict is wrong, diagnose and fix `crucible/gates.py` or `crucible/verify.py`. Repeat until correct.

**Relevant Context**
- `agent.md` §PHASE 2, Step 2.3 — exact four findings and expected outcomes.
- All API tests must use `TestClient(app, raise_server_exceptions=False)` so server exceptions appear as 500 responses rather than test errors.
- The conftest reset fixture in `demo-app/tests/conftest.py` must also be available to the selftest tests via the worktree copy.

---

## Open Questions Before Implementation

1. **Python version pinning**: should `pyproject.toml` pin `requires-python = ">=3.11"` or a tighter range?
2. **Git worktree root**: the verifier runs `git worktree add` — should this be run from the repo root (where `.git` lives), or from `demo-app/`? The repo root is assumed in this plan; confirm if the structure differs.
3. **`tests/test_verifier.py` location**: is this in `<repo-root>/tests/` (tests of the Crucible CLI) or `demo-app/tests/`? This plan puts it in `<repo-root>/tests/` — confirm.

---

## Status Summary

| Sub-Task | Phase | Status |
|---|---|---|
| 1. Project skeleton | 0 | `[ ] pending` |
| 2. Base service on `main` | 1.1 | `[ ] pending` |
| 3. Spec and ticket docs | 1.2 | `[ ] pending` |
| 4. Feature branches (planted bugs) | 1.3 | `[ ] pending` — needs human input |
| 5. Verifier core | 2.1–2.2 | `[ ] pending` |
| 6. Self-test run | 2.3 | `[ ] pending` |
