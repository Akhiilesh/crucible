# AGENT.md — Crucible build instructions

You are the development agent for **Crucible**, an entry in the IBM Bob 2.0 Hackathon (lablab.ai).
Work through the phases below **in order**. Do not skip a gate. Do not start a phase until the
previous gate has passed and the human has confirmed the session export.

---

## 1. What we are building

Crucible is a code-review agent that only reports a bug when it can **prove** it with a failing
test, then fixes it.

- **Workflow improved:** pull-request code review
- **Problem:** AI reviewers leave many comments, most are wrong or vague, developers ignore them,
  real bugs still reach main.
- **Solution:** 4 parallel attacker subagents try to break a PR. Each suspicion must become a pytest
  test that fails on the PR. A deterministic Python verifier keeps only proven findings. A fixer
  agent patches the code until every proof test passes. A report shows proof, fix and scorecard.
- **Core principle:** the AI does the thinking (intent, attacks, fixes). The Python CLI does the
  judging (verify, score, report). The AI never grades its own work.

---

## 2. Global rules (apply to every phase)

1. Python 3.11, FastAPI, pytest, Typer, Jinja2. One language only.
2. Commit after every passing gate with a clear message.
3. Never invent numbers. Metrics come only from files in `runs/`.
4. Never read or create files outside the repo.
5. Never read `PLANTED_BUGS.md` or any file listing planted bugs. If you find one, stop and tell the human.
6. Attacker subagents must **not** read this `agent.md` file. They read only `.bob/playbook/*` and `demo-app/`.
7. At the end of every phase, print: `PHASE <n> COMPLETE — human: export the Bob task session report to bob-sessions/phase<n>-<name>.md`. Then stop and wait.
8. If something fails 3 times, stop and explain the blocker instead of guessing.
9. Keep changes minimal and on-spec. No extra features.

---

## 3. Repo structure (target)

```text
crucible/
  agent.md                # this file
  .bob/playbook/          # intent, 4 attacker lenses, common rules, fixer
  crucible/               # CLI: cli.py, verify.py, gates.py, report.py
  demo-app/               # FastAPI service under review
    app/                  # application code
    tests/                # normal tests (+ tests/crucible/ for accepted proofs)
    spec/orders.md        # numbered product rules (R1, R2, ...)
    spec/tickets/         # PR-1-refunds.md, PR-2-discounts.md, PR-3-bulk-cancel.md
  runs/<pr>/              # intent.json, findings.json, verdicts.json, timing.json, report.*
  bob-sessions/           # exported Bob task session reports (mandatory for judging)
  README.md
```

---

## 4. Data contracts

### Finding record (`runs/<pr>/findings.json` is a list of these)

```json
{
  "id": "F-003",
  "lens": "spec",
  "claim": "Refund window counted from created_at, spec says delivered_at",
  "basis": "spec/orders.md#R12",
  "test_path": "runs/pr-1-refunds/tests/test_f003.py"
}
```

### Verdict record (`runs/<pr>/verdicts.json` adds these fields)

```json
{
  "gate_results": {
    "fails_on_pr": true,
    "blame": "passes_on_base | new_code | pre_existing",
    "repro": "3/3",
    "grounded": true
  },
  "verdict": "PROVEN | REJECTED | UNFIXED",
  "reason": "human-readable reason for any rejection",
  "fix_commit": "a1b2c3d or null"
}
```

### Allowed `basis` values

- `spec/orders.md#<rule id>` — the rule id must exist in the spec file
- Universal properties: `no_5xx`, `no_unhandled_exception`, `no_data_leak`, `no_negative_money`, `no_double_effect`

---

## 5. Proof gates (the heart of the product)

A finding is **PROVEN** only if all four gates pass. Any failure = **REJECTED** with the gate named in `reason`.

| Gate | Check | Rejection reason |
|---|---|---|
| G1 Fails on PR | JUnit shows `<failure>` (assertion). `<error>` = broken test | `test broken` |
| G2 Blame | Passes on base → ok. Fails on base but the targeted endpoint/function is added in `git diff main...<pr>` → ok (`new_code`). Else reject | `pre-existing behaviour` |
| G3 Reproducible | Fails 3 of 3 runs, fresh subprocess each | `flaky` |
| G4 Grounded | `basis` is a real spec rule id or an allowed universal property | `ungrounded` |

After fixing: if a PROVEN finding's test still fails after 3 fix attempts → **UNFIXED**.

---

## PHASE 0 — Setup

**Task**

Create the project skeleton:

- `crucible/__init__.py`, `crucible/cli.py` (Typer app with placeholder commands `verify` and `report`)
- `.bob/playbook/`, `demo-app/`, `runs/.gitkeep`, `bob-sessions/.gitkeep`
- `README.md` (title + one line)
- `pyproject.toml` with deps: fastapi, uvicorn, pytest, httpx, typer, jinja2, pydantic
- `.gitignore`: Python defaults + `runs/*/worktrees/`

Initialise git, commit `chore: project skeleton`. Run `python -m crucible.cli --help` and show output.

**Gate:** CLI help prints.

---

## PHASE 1 — Sample app

### Step 1.1 — Base service (branch `main`)

Build a FastAPI "orders and refunds" service in `demo-app/` with an in-memory store.

Models:
- `User(id, name)`
- `Product(id, name, price_paise: int, stock: int)`
- `Order(id, user_id, items: list[{product_id, qty}], total_paise, status, created_at, delivered_at | None)`
  where status ∈ `placed | delivered | cancelled | refunded`

Endpoints:
- `POST /orders` — create order, reduce stock, compute total
- `GET /orders/{id}`
- `POST /orders/{id}/deliver` — set status delivered + `delivered_at`
- `POST /orders/{id}/cancel` — only if status is `placed`; restore stock

Every request identifies the user via header `X-User-Id`. Users may only access their own orders (403 otherwise).

Write at least 15 pytest tests in `demo-app/tests/` using `fastapi.testclient.TestClient`, with a
`conftest.py` fixture that resets the store between tests. All must pass.

Write `demo-app/spec/orders.md`: numbered rules, one per line (`R1: ...`, `R2: ...`).

Commit `feat: demo orders service`.

### Step 1.2 — Spec for upcoming features (branch `main`)

Append rules to `demo-app/spec/orders.md`, continuing the numbering:

Refunds
- Refunds are allowed only for delivered orders.
- The refund window is 14 days counted from `delivered_at`, not `created_at`.
- Refund amount must be greater than 0 and at most the order total.
- A refunded order cannot be refunded again.

Discounts
- Discount codes give a percentage off, between 1 and 50 inclusive.
- A discount can only be applied by the owner of the order.
- The order total can never go below 0.

Bulk cancel
- `POST /orders/bulk-cancel` takes a list of order ids.
- An empty list returns 400.
- Stock is restored only for orders that were actually cancelled.

Create `demo-app/spec/tickets/PR-1-refunds.md`, `PR-2-discounts.md`, `PR-3-bulk-cancel.md`:
4–6 lines each, Jira style, referencing rule ids. Commit to `main`.

### Step 1.3 — Feature branches

**Wait for the human.** The human will paste the planted-bug instructions for the three branches
directly in chat. Implement exactly what they say on branches `pr-1-refunds`, `pr-2-discounts`,
`pr-3-bulk-cancel`. Do **not** write the bug list to any file in the repo. Do not add comments that
reveal bugs. Feature tests on each branch must pass.

**Gate:** `main` + 3 branches exist, all test suites green. Show `git branch` and results.

---

## PHASE 2 — Verifier (most important)

### Step 2.1 — Plan first

Using sections 4 and 5 of this file, write an implementation plan for `crucible/verify.py` and
`crucible/gates.py`: files, functions, worktree handling, JUnit parsing, G2 new-code detection.
Show the plan and wait for approval before coding.

### Step 2.2 — Implement

CLI: `python -m crucible.cli verify --pr <branch> --base main --run-dir runs/<pr> [--keep]`

1. Create git worktrees: `runs/<pr>/worktrees/pr` and `runs/<pr>/worktrees/base`.
2. For each finding, copy its test into `demo-app/tests/crucible/` in both worktrees.
3. Run pytest on that single file with `--junitxml`, fresh subprocess, `cwd=demo-app`.
4. Apply gates G1–G4 exactly as in section 5.
5. Write `runs/<pr>/verdicts.json`. Print a summary table of PROVEN / REJECTED counts.
6. Remove worktrees unless `--keep`.

Write unit tests for the verifier in `tests/test_verifier.py`.

### Step 2.3 — Self-test

Create `runs/verifier-selftest/` against `pr-1-refunds` with 4 hand-written findings:

1. **Real:** refund window uses `created_at` (basis = the refund-window rule id)
2. **Fake wrong expectation:** asserts refunds allowed for `placed` orders, basis cites a non-existent rule
3. **Fake broken:** test imports a module that does not exist
4. **Fake pre-existing:** asserts something that already fails on `main`, unrelated to the PR

API tests must use `TestClient(app, raise_server_exceptions=False)`.

Expected: 1 PROVEN, 3 REJECTED with correct reasons. If results differ, fix the verifier, not the tests.

**Gate:** exactly 1 PROVEN, 3 REJECTED, correct reasons.

---

## PHASE 3 — Playbook and attack

### Step 3.1 — Write playbook files in `.bob/playbook/`

**intent.md**
> Given a PR branch: read `git diff main...<pr>`, the matching ticket in `demo-app/spec/tickets/`,
> and `demo-app/spec/orders.md`. Output `runs/<pr>/intent.json`: a list of
> `{behaviour, rule_id, endpoints}` for rules relevant to the diff only.

**attack-common.md** (rules for all attackers)
> - Write one pytest file per finding in `runs/<pr>/tests/test_<id>.py`.
> - Use `TestClient(app, raise_server_exceptions=False)` and the conftest reset fixture.
> - Each test asserts the **correct** behaviour per spec or universal property, so it fails only if the bug exists.
> - Append `{id, lens, claim, basis, test_path}` to `runs/<pr>/findings/<lens>.json`.
> - `claim` is one plain-English line. `basis` is a spec rule id or an allowed universal property.
> - Max 5 findings per lens. No style comments. Never modify app code.
> - Never read `agent.md`, `PLANTED_BUGS.md`, or files outside the repo.

**attack-edge.md** — boundaries: zero, negative, empty, huge, missing fields, wrong types.

**attack-security.md** — authorization with another user's `X-User-Id`, IDOR, input injection, information leaks in errors.

**attack-state.md** — ordering, repeated calls, double effects, state transitions the spec forbids.

**attack-spec.md** — go through `intent.json` rule by rule and try to violate each one.

**fixer.md**
> For each PROVEN finding in `runs/<pr>/verdicts.json`: fix app code on the PR branch (never edit
> the proof test), run the full test suite, max 3 attempts per finding. Commit each fix separately
> as `fix(<id>): <claim>`. Record `fix_commit`, or mark `UNFIXED`.

Commit `feat: crucible playbook`.

### Step 3.2 — Intent

Follow `.bob/playbook/intent.md` for `pr-1-refunds`. Show `intent.json`.

### Step 3.3 — Parallel attack (the showpiece)

Spawn **4 subagents in parallel**, one per lens. Each reads `attack-common.md`, its lens file, and
`runs/pr-1-refunds/intent.json`, and writes only to `runs/pr-1-refunds/tests/` and
`runs/pr-1-refunds/findings/<lens>.json`.

When all finish:
- Merge into `runs/pr-1-refunds/findings.json` with unique ids `F-001...`
- Log start/end time per subagent in `runs/pr-1-refunds/timing.json`
- Run `python -m crucible.cli verify --pr pr-1-refunds --base main --run-dir runs/pr-1-refunds`

If parallel subagents are not available, run the 4 lenses as separate tasks, log timing, and
report this honestly to the human (it goes in the README).

**Gate:** PR-1 has at least 1 PROVEN and 1 REJECTED finding.

---

## PHASE 4 — Fixer and report

### Step 4.1 — Fix

Follow `.bob/playbook/fixer.md` for `runs/pr-1-refunds/verdicts.json`. Re-run the verifier after
fixes: every previously PROVEN test must now pass on the PR branch. Update `verdicts.json`. Show each fix diff.

### Step 4.2 — Report

Implement `python -m crucible.cli report --run-dir runs/<pr>` producing `report.md` and a
self-contained `report.html` (Jinja2, no external assets, light and dark mode):

- Header: PR name, time taken (from `timing.json`), verdict counts
- Scorecard: raw suspicions, proven, rejected, fixed, unfixed, precision
- One card per PROVEN finding: claim, lens, spec rule text quoted from `orders.md`, proof test code, fix diff, red→green status
- Collapsed "Noise rejected" section: each rejected finding with reason

**Gate:** PR-1 fully green with report generated.

---

## PHASE 5 — Full runs and baseline

### Step 5.1 — Run remaining PRs

Run the full pipeline (intent → 4 parallel attackers → verify → fix → verify → report) for
`pr-2-discounts`, then `pr-3-bulk-cancel`. Do not change the playbook between PRs. Log timing per stage.

### Step 5.2 — Baseline review

For each PR, in a **separate** task with no access to the playbook, use this prompt and save the
output to `runs/<pr>/baseline.md`:

> You are reviewing pull request `<branch>` against `main`. Review the diff and leave code review
> comments as you normally would. Output a numbered list of comments.

### Step 5.3 — Summary

Create `runs/summary.json` and `runs/summary.md` across all 3 PRs:
- Baseline comment count vs Crucible proven findings
- How many baseline comments point to a real bug (match against PROVEN findings by endpoint + behaviour)
- Precision, fix rate, total time per PR

Use only files in `runs/`. The human will calculate recall against the private planted-bug list.

**Gate:** real numbers for every metric.

---

## PHASE 6 — Ship

### Step 6.1 — README

Write `README.md` for judges:

1. Problem
2. Solution
3. How it works (mermaid: intent → 4 attackers → verifier → fixer → report)
4. Proof gates table
5. How IBM Bob was used (table: stage, Bob feature, session report file in `bob-sessions/`)
6. Results (from `runs/summary.md`, real numbers only)
7. Quick start commands
8. Limitations (Python only, planted bugs in a sample app, subagent parallelism notes)
9. Future work (GitHub App, CI via Bob Shell, more languages, mutation check)

### Step 6.2 — Optional dashboard (only if time allows)

`dashboard/index.html`: self-contained page built by `scripts/build_dashboard.py`, which embeds
`runs/summary.json` and `runs/*/verdicts.json`. Scorecard tiles, per-PR findings with red→green
status, rejected-noise list. Light and dark mode, no external assets.

**Gate:** repo ready, all sessions exported by every team member, human records video and submits.

---

## 7. Cut list (if behind schedule, drop in this order)

1. Dashboard
2. PR-3
3. Baseline comparison
4. Mutation check

**Never cut:** the verifier, the proof gates, or Bob session exports.

---

## 8. Recovery rules

| Situation | What to do |
|---|---|
| An attacker modified app code | Revert everything outside `runs/`, re-run that lens |
| Most findings rejected as `test broken` | Show 2 JUnit outputs, fix the test template in `attack-common.md` |
| Fixer edited a proof test | Revert; proof tests are read-only |
| Duplicate findings | Keep max 5 per lens, dedupe by endpoint + behaviour |
| A step fails 3 times | Stop and explain the blocker to the human |

---

## 9. Submission checklist (human)

- [ ] Public GitHub repo with README
- [ ] `bob-sessions/` with reports from every team member
- [ ] Video under 3 minutes (disclose that bugs were planted in a sample app)
- [ ] Slide deck, 8–10 slides
- [ ] Short + long descriptions, cover image on lablab
- [ ] Submitted before Sep 27, 15:00 UTC (20:30 IST)
