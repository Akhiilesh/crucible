"""
crucible/verify.py — Orchestration layer for the Crucible verifier.

Owns all I/O: git worktrees, subprocess pytest runs, JSON reading/writing.
Pure gate logic lives in crucible/gates.py.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from crucible.gates import (
    after_fix_status,
    gate_g1_fails_on_pr,
    gate_g2_blame,
    gate_g3_reproducible,
    gate_g4_grounded,
    parse_junit,
)


# ── Git helpers ───────────────────────────────────────────────────────────────

def _git(*args: str, cwd: Path | None = None) -> str:
    """Run a git command and return stdout. Raises on non-zero exit."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed:\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def resolve_sha(branch: str, repo_root: Path) -> str:
    """Return the full commit SHA for a branch."""
    return _git("rev-parse", branch, cwd=repo_root)


# ── Worktree management ───────────────────────────────────────────────────────

def setup_worktrees(
    pr_branch: str,
    base_branch: str,
    run_dir: Path,
    repo_root: Path,
) -> tuple[Path, Path]:
    """Create detached worktrees for the PR and base branches.

    1. git worktree prune (clean stale references)
    2. Remove any leftover worktree dirs from a previous interrupted run
    3. Resolve SHAs (avoids "already checked out" errors on main)
    4. git worktree add --detach <path> <sha>
    Returns (pr_worktree, base_worktree).
    """
    _git("worktree", "prune", cwd=repo_root)

    pr_worktree = run_dir / "worktrees" / "pr"
    base_worktree = run_dir / "worktrees" / "base"

    for wt in (pr_worktree, base_worktree):
        if wt.exists():
            shutil.rmtree(wt)

    _add_worktree(pr_worktree, pr_branch, repo_root)
    _add_worktree(base_worktree, base_branch, repo_root)

    return pr_worktree, base_worktree


def _add_worktree(path: Path, branch: str, repo_root: Path) -> None:
    """Add a detached worktree at the branch's current SHA (works even if checked out)."""
    if path.exists():
        shutil.rmtree(path)
    _git("worktree", "add", "--detach", str(path), resolve_sha(branch, repo_root), cwd=repo_root)


def teardown_worktrees(run_dir: Path, repo_root: Path) -> None:
    """Remove both worktrees and prune stale references."""
    for name in ("pr", "base"):
        wt = run_dir / "worktrees" / name
        try:
            _git("worktree", "remove", "--force", str(wt), cwd=repo_root)
        except RuntimeError:
            # Already gone — not an error
            if wt.exists():
                shutil.rmtree(wt)
    _git("worktree", "prune", cwd=repo_root)


# ── Pytest runner ─────────────────────────────────────────────────────────────

def copy_test_to_worktree(test_path: Path, worktree: Path) -> Path:
    """Copy a proof test into <worktree>/demo-app/tests/crucible/.

    Creates tests/crucible/__init__.py if absent so pytest's rootdir
    insertion doesn't break `import app` or conftest fixtures.
    Returns the destination path.
    """
    dest_dir = worktree / "demo-app" / "tests" / "crucible"
    dest_dir.mkdir(parents=True, exist_ok=True)

    init_file = dest_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    dest = dest_dir / test_path.name
    shutil.copy2(test_path, dest)
    return dest


def run_pytest_once(
    test_file: str,
    worktree: Path,
    junit_out: Path,
    timeout: int = 60,
) -> str:
    """Run a single proof-test file and return the outcome string.

    Outcome is one of: "failure" | "error" | "passed" | "skipped" | "timeout"

    - Deletes junit_out before running (stale file → misleading result)
    - Uses sys.executable so the same venv is always used
    - cwd is <worktree>/demo-app
    - A missing or empty JUnit file after the run returns "error"
    """
    junit_out.parent.mkdir(parents=True, exist_ok=True)
    if junit_out.exists():
        junit_out.unlink()

    cmd = [
        sys.executable, "-m", "pytest",
        f"tests/crucible/{test_file}",
        f"--junitxml={junit_out}",
        "-q",
        "-p", "no:cacheprovider",
    ]

    try:
        subprocess.run(
            cmd,
            cwd=worktree / "demo-app",
            timeout=timeout,
            capture_output=True,
        )
    except subprocess.TimeoutExpired:
        return "timeout"

    if not junit_out.exists() or junit_out.stat().st_size == 0:
        return "error"

    return parse_junit(junit_out.read_text())


# ── Per-finding verification ──────────────────────────────────────────────────

def _null_verdict(finding: dict, reason: str) -> dict:
    """Return a REJECTED verdict for a finding that couldn't be run (e.g. missing test)."""
    return {
        **finding,
        "gate_results": {
            "fails_on_pr": None,
            "blame": None,
            "repro": None,
            "grounded": None,
        },
        "verdict": "REJECTED",
        "reason": reason,
        "fix_commit": None,
    }


def verify_finding(
    finding: dict,
    pr_worktree: Path,
    base_worktree: Path,
    diff_text: str,
    spec_text: str,
    run_dir: Path,
    repo_root: Path,
    intent_rule_ids: set[str] | None = None,
) -> dict:
    """Apply G4 → G1 → G3 → G2 gates to a single finding.

    Short-circuits on the first failure. JUnit files are written to
    run_dir/junit/ and kept regardless of --keep.

    Returns a verdict dict matching agent.md §4.
    """
    fid = finding["id"]
    basis = finding.get("basis", "")
    raw_test_path = finding.get("test_path", "")

    # Resolve test_path relative to repo_root
    test_path = (repo_root / raw_test_path) if raw_test_path else None
    if not test_path or not test_path.exists():
        return _null_verdict(finding, "test broken")

    test_source = test_path.read_text()
    junit_dir = run_dir / "junit"

    # Initialise gate result tracking
    gate_results: dict[str, object] = {
        "fails_on_pr": None,
        "blame": None,
        "repro": None,
        "grounded": None,
    }

    # ── G4 Grounded (static, always first) ──────────────────────────────────
    g4_pass, g4_detail = gate_g4_grounded(basis, spec_text, intent_rule_ids)
    gate_results["grounded"] = g4_pass
    if not g4_pass:
        return {**finding, "gate_results": gate_results,
                "verdict": "REJECTED", "reason": "ungrounded", "fix_commit": None}

    # Copy test into both worktrees
    copy_test_to_worktree(test_path, pr_worktree)
    copy_test_to_worktree(test_path, base_worktree)
    test_filename = test_path.name

    # ── G1 Fails on PR (run 1 of 3) ─────────────────────────────────────────
    junit_pr1 = junit_dir / f"{fid}-pr1.xml"
    outcome_pr1 = run_pytest_once(test_filename, pr_worktree, junit_pr1)

    g1_pass, g1_detail = gate_g1_fails_on_pr(outcome_pr1)
    gate_results["fails_on_pr"] = g1_pass
    if not g1_pass:
        return {**finding, "gate_results": gate_results,
                "verdict": "REJECTED", "reason": g1_detail, "fix_commit": None}

    # ── G3 Reproducible (runs 2 and 3) ──────────────────────────────────────
    junit_pr2 = junit_dir / f"{fid}-pr2.xml"
    junit_pr3 = junit_dir / f"{fid}-pr3.xml"
    outcome_pr2 = run_pytest_once(test_filename, pr_worktree, junit_pr2)
    outcome_pr3 = run_pytest_once(test_filename, pr_worktree, junit_pr3)

    all_outcomes = [outcome_pr1, outcome_pr2, outcome_pr3]
    g3_pass, repro = gate_g3_reproducible(all_outcomes)
    gate_results["repro"] = repro
    if not g3_pass:
        return {**finding, "gate_results": gate_results,
                "verdict": "REJECTED", "reason": "flaky", "fix_commit": None}

    # ── G2 Blame (one base run) ───────────────────────────────────────────────
    junit_base = junit_dir / f"{fid}-base.xml"
    base_outcome = run_pytest_once(test_filename, base_worktree, junit_base)

    g2_pass, blame = gate_g2_blame(base_outcome, diff_text, test_source)
    gate_results["blame"] = blame
    if not g2_pass:
        return {**finding, "gate_results": gate_results,
                "verdict": "REJECTED", "reason": "pre-existing behaviour", "fix_commit": None}

    # ── All gates passed ─────────────────────────────────────────────────────
    return {
        **finding,
        "gate_results": gate_results,
        "verdict": "PROVEN",
        "reason": "",
        "fix_commit": None,
    }


# ── Top-level orchestrator ────────────────────────────────────────────────────

def run_verification(
    pr_branch: str,
    base_branch: str,
    run_dir: Path,
    repo_root: Path,
    keep: bool = False,
) -> None:
    """Run the full verification pipeline for one PR.

    1. Load findings.json
    2. Set up git worktrees (PR and base)
    3. Read spec text from the base worktree
    4. Compute git diff (app code only, once per PR)
    5. Verify each finding through G4 → G1 → G3 → G2
    6. Write verdicts.json
    7. Print summary table + counts
    8. Tear down worktrees (unless --keep)
    """
    # Resolve run_dir relative to repo_root if needed
    if not run_dir.is_absolute():
        run_dir = repo_root / run_dir

    findings_path = run_dir / "findings.json"
    if not findings_path.exists():
        raise FileNotFoundError(f"findings.json not found in {run_dir}")

    findings: list[dict] = json.loads(findings_path.read_text())

    # G4 also requires cited rules to be listed in the run's intent.json, when there is one
    intent_path = run_dir / "intent.json"
    intent_rule_ids = (
        {e["rule_id"] for e in json.loads(intent_path.read_text())}
        if intent_path.exists() else None
    )

    started = _now()
    pr_worktree: Path | None = None
    base_worktree: Path | None = None

    try:
        pr_worktree, base_worktree = setup_worktrees(
            pr_branch, base_branch, run_dir, repo_root
        )

        # Read spec from base worktree so G4 uses the same spec the base branch has
        spec_path = base_worktree / "demo-app" / "spec" / "orders.md"
        spec_text = spec_path.read_text() if spec_path.exists() else ""

        # One diff per PR — app code only, so test helpers don't count as "new code"
        diff_text = _git(
            "diff", f"{base_branch}...{pr_branch}", "--", "demo-app/app",
            cwd=repo_root,
        )

        verdicts: list[dict] = []
        for finding in findings:
            print(f"  verifying {finding['id']} ({finding.get('lens', '?')}) …")
            verdict = verify_finding(
                finding, pr_worktree, base_worktree,
                diff_text, spec_text, run_dir, repo_root, intent_rule_ids,
            )
            verdicts.append(verdict)

    finally:
        if not keep and pr_worktree is not None:
            teardown_worktrees(run_dir, repo_root)

    # Write verdicts
    verdicts_path = run_dir / "verdicts.json"
    verdicts_path.write_text(json.dumps(verdicts, indent=2))
    record_timing(run_dir, "verify", started, _now())

    # Print summary table
    proven = sum(1 for v in verdicts if v["verdict"] == "PROVEN")
    rejected = sum(1 for v in verdicts if v["verdict"] == "REJECTED")

    _print_summary(verdicts, proven, rejected)


def _print_summary(verdicts: list[dict], proven: int, rejected: int) -> None:
    """Print a summary table to stdout."""
    col_id = max(len(v["id"]) for v in verdicts) if verdicts else 4
    col_lens = max(len(v.get("lens", "")) for v in verdicts) if verdicts else 4
    col_verdict = 8
    header = (
        f"{'ID':<{col_id}}  {'LENS':<{col_lens}}  {'VERDICT':<{col_verdict}}  REASON"
    )
    print()
    print(header)
    print("─" * (len(header) + 20))
    for v in verdicts:
        print(
            f"{v['id']:<{col_id}}  "
            f"{v.get('lens', ''):<{col_lens}}  "
            f"{v['verdict']:<{col_verdict}}  "
            f"{v.get('reason', '')}"
        )
    print()
    print(f"PROVEN: {proven}   REJECTED: {rejected}   TOTAL: {proven + rejected}")
    print()


# ── After-fix check ───────────────────────────────────────────────────────────

AFTER_FIX_RUNS = 3


def run_after_fix_check(
    pr_branch: str,
    run_dir: Path,
    repo_root: Path,
    keep: bool = False,
) -> None:
    """Re-run every PROVEN/UNFIXED proof test on the fixed PR branch.

    A proof test counts as fixed only if it passes on all AFTER_FIX_RUNS fresh
    runs. A PROVEN finding whose test still does not pass becomes UNFIXED.
    Also runs the full demo-app suite once and writes run_dir/fix_check.json.
    """
    if not run_dir.is_absolute():
        run_dir = repo_root / run_dir

    verdicts_path = run_dir / "verdicts.json"
    verdicts: list[dict] = json.loads(verdicts_path.read_text())
    started = _now()

    pr_worktree = run_dir / "worktrees" / "pr"
    _git("worktree", "prune", cwd=repo_root)
    _add_worktree(pr_worktree, pr_branch, repo_root)
    try:
        pr_sha = _git("rev-parse", "--short", pr_branch, cwd=repo_root)

        # Full suite on the branch exactly as committed (before copying in any
        # UNFIXED proof tests, which are deliberately not committed)
        suite = subprocess.run(
            [sys.executable, "-m", "pytest", "demo-app/tests", "-q", "-p", "no:cacheprovider"],
            cwd=pr_worktree, capture_output=True, text=True, timeout=300,
        )
        lines = [ln for ln in suite.stdout.splitlines() if ln.strip()]
        fix_check = {
            "pr": pr_branch,
            "pr_sha": pr_sha,
            "suite_green": suite.returncode == 0,
            "suite_summary": lines[-1] if lines else "",
        }

        for v in verdicts:
            if v["verdict"] not in ("PROVEN", "UNFIXED"):
                continue
            test_path = repo_root / v["test_path"]
            copy_test_to_worktree(test_path, pr_worktree)
            outcomes = [
                run_pytest_once(
                    test_path.name, pr_worktree,
                    run_dir / "junit" / f"{v['id']}-fixed{i}.xml",
                )
                for i in range(1, AFTER_FIX_RUNS + 1)
            ]
            fixed, runs = after_fix_status(outcomes)
            v["after_fix"] = {"passes": fixed, "runs": runs, "pr_sha": pr_sha}
            if not fixed and v["verdict"] == "PROVEN":
                v["verdict"] = "UNFIXED"

    finally:
        if not keep:
            teardown_worktrees(run_dir, repo_root)

    verdicts_path.write_text(json.dumps(verdicts, indent=2))
    (run_dir / "fix_check.json").write_text(json.dumps(fix_check, indent=2))
    record_timing(run_dir, "verify_after_fix", started, _now())

    print()
    for v in verdicts:
        if "after_fix" in v:
            af = v["after_fix"]
            print(f"{v['id']:<8} {v['verdict']:<9} passes after fix: {af['runs']}  "
                  f"fix_commit={v.get('fix_commit')}")
    print(f"\nFull suite on {pr_branch}@{pr_sha}: {fix_check['suite_summary']}\n")


# ── Timing ────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(tz=timezone.utc).replace(microsecond=0)


def record_timing(run_dir: Path, stage: str, start: datetime, end: datetime) -> None:
    """Merge {stage: {start, end, seconds, by}} into run_dir/timing.json."""
    path = run_dir / "timing.json"
    timing = json.loads(path.read_text()) if path.exists() else {"pr": run_dir.name}
    timing[stage] = {
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seconds": int((end - start).total_seconds()),
        "by": "crucible-cli",
    }
    path.write_text(json.dumps(timing, indent=2))
