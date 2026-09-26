"""
crucible/summary.py — Cross-PR scorecard: runs/summary.json and runs/summary.md.

Uses only files in runs/. Baseline numbers come from runs/<pr>/baseline.md (a
numbered list of plain-AI review comments) and runs/<pr>/baseline_matches.json
({"matches": [{"comment": n, "finding": "F-00x"}], "matched_by": "..."}),
which records which baseline comments point at a PROVEN finding. Missing files
are reported as null, never guessed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PRS = ("pr-1-refunds", "pr-2-discounts", "pr-3-bulk-cancel")
STAGES = ("intent", "attack", "verify", "fix", "verify_after_fix")


def _load(path: Path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def count_numbered_comments(markdown: str) -> int:
    """Count top-level numbered list items ("1. ...", "2) ...")."""
    return len(re.findall(r"^\d+[.)]\s+\S", markdown, re.MULTILINE))


def _pct(num: int | None, den: int | None) -> float | None:
    return round(100 * num / den, 1) if num is not None and den else None


def pr_summary(run_dir: Path) -> dict | None:
    verdicts = _load(run_dir / "verdicts.json")
    if verdicts is None:
        return None
    timing = _load(run_dir / "timing.json", {})
    fix_check = _load(run_dir / "fix_check.json", {})

    proven = [v for v in verdicts if v["verdict"] in ("PROVEN", "UNFIXED")]
    fixed = [v for v in proven if v.get("after_fix", {}).get("passes")]
    reasons: dict[str, int] = {}
    for v in verdicts:
        if v["verdict"] == "REJECTED":
            reasons[v["reason"]] = reasons.get(v["reason"], 0) + 1

    baseline_md = run_dir / "baseline.md"
    baseline_count = count_numbered_comments(baseline_md.read_text()) if baseline_md.exists() else None
    matches = _load(run_dir / "baseline_matches.json")
    matched_comments = (
        len({m["comment"] for m in matches["matches"]}) if matches is not None else None
    )
    matched_findings = (
        sorted({m["finding"] for m in matches["matches"]}) if matches is not None else None
    )

    stage_seconds = {
        s: timing[s]["seconds"] for s in STAGES
        if isinstance(timing.get(s), dict) and "seconds" in timing[s]
    }
    return {
        "pr": run_dir.name,
        "raw_suspicions": len(verdicts),
        "proven": len(proven),
        "rejected": len(verdicts) - len(proven),
        "rejected_by_reason": reasons,
        "distinct_fixes": len({v["fix_commit"] for v in fixed if v.get("fix_commit")}),
        "fixed": len(fixed),
        "unfixed": len(proven) - len(fixed),
        "precision_pct": _pct(len(proven), len(proven)),
        "suspicions_confirmed_pct": _pct(len(proven), len(verdicts)),
        "fix_rate_pct": _pct(len(fixed), len(proven)),
        "suite_green_after_fix": fix_check.get("suite_green"),
        "attack_mode": timing.get("attack", {}).get("mode"),
        "stage_seconds": stage_seconds,
        "total_seconds": sum(stage_seconds.values()),
        "baseline_comments": baseline_count,
        "baseline_comments_on_proven_bugs": matched_comments,
        "baseline_precision_pct": _pct(matched_comments, baseline_count),
        "proven_findings_seen_by_baseline": matched_findings,
        "baseline_matched_by": matches.get("matched_by") if matches else None,
    }


def _total(prs: list[dict], key: str) -> int | None:
    vals = [p[key] for p in prs]
    return None if any(v is None for v in vals) else sum(vals)


def build_summary(runs_dir: Path) -> dict:
    prs = [s for s in (pr_summary(runs_dir / pr) for pr in PRS) if s]
    totals = {k: _total(prs, k) for k in (
        "raw_suspicions", "proven", "rejected", "distinct_fixes", "fixed", "unfixed",
        "total_seconds", "baseline_comments", "baseline_comments_on_proven_bugs",
    )}
    totals["precision_pct"] = _pct(totals["proven"], totals["proven"])
    totals["suspicions_confirmed_pct"] = _pct(totals["proven"], totals["raw_suspicions"])
    totals["fix_rate_pct"] = _pct(totals["fixed"], totals["proven"])
    totals["baseline_precision_pct"] = _pct(
        totals["baseline_comments_on_proven_bugs"], totals["baseline_comments"])
    return {"prs": prs, "totals": totals}


def _fmt(v, suffix: str = "") -> str:
    return "not recorded" if v is None else f"{v}{suffix}"


def render_markdown(summary: dict) -> str:
    prs, t = summary["prs"], summary["totals"]
    cols = [p["pr"] for p in prs] + ["**total**"]
    rows = [
        ("Raw suspicions", "raw_suspicions", ""),
        ("Proven (failing test, 4 gates)", "proven", ""),
        ("Rejected as noise", "rejected", ""),
        ("Distinct fixes", "distinct_fixes", ""),
        ("Fixed (proof passes 3/3)", "fixed", ""),
        ("Unfixed (flagged for a human)", "unfixed", ""),
        ("Precision of reported findings", "precision_pct", "%"),
        ("Suspicions confirmed", "suspicions_confirmed_pct", "%"),
        ("Fix rate", "fix_rate_pct", "%"),
        ("Pipeline time (s)", "total_seconds", ""),
        ("Baseline review comments", "baseline_comments", ""),
        ("Baseline comments on a proven bug", "baseline_comments_on_proven_bugs", ""),
        ("Baseline precision", "baseline_precision_pct", "%"),
    ]
    out = [
        "# Crucible — results across 3 PRs",
        "",
        "Generated by `crucible summary` from files in `runs/` only.",
        "",
        "| Metric | " + " | ".join(cols) + " |",
        "|---|" + "---|" * len(cols),
    ]
    for label, key, suffix in rows:
        vals = [_fmt(p[key], suffix) for p in prs] + [_fmt(t.get(key), suffix)]
        out.append(f"| {label} | " + " | ".join(vals) + " |")
    out += [
        "",
        "**Precision** = proven ÷ findings reported to the reviewer (only proven findings are "
        "reported). **Suspicions confirmed** = proven ÷ raw attacker suspicions; the rest was "
        "filtered out as noise by the verifier. **Baseline precision** = baseline comments that "
        "point at a proven bug ÷ all baseline comments.",
        "",
        "## Noise rejected, by reason",
        "",
    ]
    for p in prs:
        reasons = ", ".join(f"{k}: {v}" for k, v in p["rejected_by_reason"].items()) or "none"
        out.append(f"- `{p['pr']}` — {reasons}")
    out += ["", "## Time per stage (seconds)", "",
            "| PR | " + " | ".join(STAGES) + " | total | attack mode |",
            "|---|" + "---|" * (len(STAGES) + 2)]
    for p in prs:
        vals = [str(p["stage_seconds"].get(s, "—")) for s in STAGES]
        out.append(f"| `{p['pr']}` | " + " | ".join(vals)
                   + f" | {p['total_seconds']} | {p['attack_mode'] or '—'} |")
    matched = [p for p in prs if p["baseline_matched_by"]]
    if matched:
        out += ["", f"Baseline comments were matched to proven findings by "
                    f"{matched[0]['baseline_matched_by']} (endpoint + behaviour)."]
    out.append("")
    return "\n".join(out)


def run_summary(runs_dir: Path) -> dict:
    summary = build_summary(runs_dir)
    (runs_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    (runs_dir / "summary.md").write_text(render_markdown(summary))
    return summary
