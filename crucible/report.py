"""
crucible/report.py — Build report.md and report.html for one verification run.

Deterministic: every number comes from files in the run directory
(verdicts.json, timing.json, fix_check.json) or from git (spec text, fix diffs).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from crucible.verify import _git

UNIVERSAL_PROPERTY_TEXT = {
    "no_5xx": "The service never answers with a 5xx server error.",
    "no_unhandled_exception": "No request raises an unhandled exception.",
    "no_data_leak": "No response exposes another user's data or internal details.",
    "no_negative_money": "No amount or total ever becomes negative.",
    "no_double_effect": "Repeating a request never applies its effect twice.",
}

STAGE_ORDER = ("intent", "attack", "verify", "fix", "verify_after_fix")

_TEMPLATES = Path(__file__).parent / "templates"


# ── Context building ──────────────────────────────────────────────────────────

def _load_json(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def _spec_rules(repo_root: Path, base: str) -> dict[str, str]:
    """Map rule id → rule text from the base branch's spec."""
    spec = _git("show", f"{base}:demo-app/spec/orders.md", cwd=repo_root)
    return dict(re.findall(r"^(R\d+):\s*(.+)$", spec, re.MULTILINE))


def _basis_text(basis: str, rules: dict[str, str]) -> tuple[str, str]:
    """Return (label, quoted text) for a finding's basis."""
    m = re.fullmatch(r"spec/orders\.md#(R\d+)", basis)
    if m:
        return m.group(1), rules.get(m.group(1), "")
    return basis, UNIVERSAL_PROPERTY_TEXT.get(basis, "")


def _fix_diff(sha: str | None, repo_root: Path) -> str:
    if not sha:
        return ""
    return _git("show", "--format=", sha, "--", "demo-app/app", cwd=repo_root)


def _diff_lines(diff: str) -> list[tuple[str, str]]:
    """Tag each diff line for styling: add, del, hunk, meta or ctx."""
    tagged = []
    for line in diff.splitlines():
        if line.startswith(("+++", "---", "diff ", "index ")):
            tagged.append(("meta", line))
        elif line.startswith("@@"):
            tagged.append(("hunk", line))
        elif line.startswith("+"):
            tagged.append(("add", line))
        elif line.startswith("-"):
            tagged.append(("del", line))
        else:
            tagged.append(("ctx", line))
    return tagged


def _pct(num: int, den: int) -> str:
    return f"{round(100 * num / den)}%" if den else "n/a"


def build_context(run_dir: Path, repo_root: Path, base: str = "main") -> dict:
    verdicts: list[dict] = _load_json(run_dir / "verdicts.json", [])
    timing: dict = _load_json(run_dir / "timing.json", {})
    fix_check: dict | None = _load_json(run_dir / "fix_check.json", None)
    rules = _spec_rules(repo_root, base)

    proven = [v for v in verdicts if v["verdict"] in ("PROVEN", "UNFIXED")]
    rejected = [v for v in verdicts if v["verdict"] == "REJECTED"]
    fixed = [v for v in proven if v.get("after_fix", {}).get("passes")]
    unfixed = [v for v in proven if v not in fixed]

    # Proofs that share a fix commit prove the same root cause
    first_by_fix: dict[str, str] = {}
    cards = []
    for v in proven:
        sha = v.get("fix_commit")
        same_as = first_by_fix.get(sha) if sha else None
        if sha and sha not in first_by_fix:
            first_by_fix[sha] = v["id"]
        label, text = _basis_text(v["basis"], rules)
        test_file = repo_root / v["test_path"]
        af = v.get("after_fix")
        cards.append({
            **v,
            "basis_label": label,
            "basis_text": text,
            "test_code": test_file.read_text() if test_file.exists() else "",
            "diff_lines": [] if same_as else _diff_lines(_fix_diff(sha, repo_root)),
            "same_fix_as": same_as,
            "red": v["gate_results"].get("repro"),
            "green": af["runs"] if af else None,
            "is_fixed": v in fixed,
        })
    unique_bugs = len(first_by_fix) + sum(1 for v in proven if not v.get("fix_commit"))

    by_reason: dict[str, list[dict]] = {}
    for v in rejected:
        by_reason.setdefault(v["reason"], []).append(v)

    stages = [
        {"name": name, **timing[name]}
        for name in STAGE_ORDER
        if isinstance(timing.get(name), dict) and "seconds" in timing[name]
    ]
    total_seconds = sum(s["seconds"] for s in stages)

    return {
        "pr": timing.get("pr", run_dir.name),
        "base": base,
        "total": len(verdicts),
        "proven": len(proven),
        "rejected": len(rejected),
        "fixed": len(fixed),
        "unfixed": len(unfixed),
        "unique_bugs": unique_bugs,
        "precision": _pct(len(proven), len(proven)),
        "confirmation_rate": _pct(len(proven), len(verdicts)),
        "cards": cards,
        "by_reason": sorted(by_reason.items(), key=lambda kv: -len(kv[1])),
        "stages": stages,
        "total_seconds": total_seconds,
        "attack_mode": timing.get("attack", {}).get("mode"),
        "lenses": timing.get("attack", {}).get("lenses", {}),
        "fix_check": fix_check,
    }


# ── Rendering ─────────────────────────────────────────────────────────────────

def _fmt_seconds(s: int) -> str:
    return f"{s // 60}m {s % 60:02d}s" if s >= 60 else f"{s}s"


def render(context: dict) -> tuple[str, str]:
    """Return (markdown, html)."""
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES),
        autoescape=lambda name: bool(name) and name.endswith(".html.j2"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["duration"] = _fmt_seconds
    md = env.get_template("report.md.j2").render(**context)
    html = env.get_template("report.html.j2").render(**context)
    return md, html


def build_report(run_dir: Path, repo_root: Path, base: str = "main") -> tuple[Path, Path]:
    if not run_dir.is_absolute():
        run_dir = repo_root / run_dir
    md, html = render(build_context(run_dir, repo_root, base))
    md_path, html_path = run_dir / "report.md", run_dir / "report.html"
    md_path.write_text(md)
    html_path.write_text(html)
    return md_path, html_path
