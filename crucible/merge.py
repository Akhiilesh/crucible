"""
crucible/merge.py — Merge per-lens attacker output into findings.json + timing.json.

Mechanical only: no finding is edited, dropped (beyond the 5-per-lens cap) or judged.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

LENSES = ("edge", "security", "state", "spec")
MAX_PER_LENS = 5
_TS = "%Y-%m-%dT%H:%M:%SZ"


def merge_findings(per_lens: dict[str, list[dict]]) -> list[dict]:
    """Assign F-001… in lens order, keeping each lens's first MAX_PER_LENS findings."""
    merged = []
    for lens in LENSES:
        for f in per_lens.get(lens, [])[:MAX_PER_LENS]:
            merged.append({
                "id": f"F-{len(merged) + 1:03d}",
                "lens_id": f["id"],
                "lens": f.get("lens", lens),
                "claim": f["claim"],
                "basis": f["basis"],
                "test_path": f["test_path"],
            })
    return merged


def _seconds(start: str, end: str) -> int:
    return int((datetime.strptime(end, _TS) - datetime.strptime(start, _TS)).total_seconds())


def attack_timing(lens_times: dict[str, dict], counts: dict[str, int]) -> dict:
    """Build the timing "attack" stage; mode is parallel only if every lens window overlaps."""
    starts = [t["start"] for t in lens_times.values()]
    ends = [t["end"] for t in lens_times.values()]
    overlapping = len(lens_times) > 1 and max(starts) < min(ends)
    return {
        "mode": "parallel" if overlapping else "sequential",
        "start": min(starts),
        "end": max(ends),
        "seconds": _seconds(min(starts), max(ends)),
        "by": "bob-subagents",
        "lenses": {
            lens: {**t, "seconds": _seconds(t["start"], t["end"]), "findings": counts.get(lens, 0)}
            for lens, t in lens_times.items()
        },
    }


def run_merge(run_dir: Path, repo_root: Path) -> list[dict]:
    if not run_dir.is_absolute():
        run_dir = repo_root / run_dir
    fdir = run_dir / "findings"

    per_lens = {
        lens: json.loads((fdir / f"{lens}.json").read_text())
        for lens in LENSES if (fdir / f"{lens}.json").exists()
    }
    merged = merge_findings(per_lens)
    (run_dir / "findings.json").write_text(json.dumps(merged, indent=2))

    timing_path = run_dir / "timing.json"
    timing = json.loads(timing_path.read_text()) if timing_path.exists() else {}
    timing["pr"] = run_dir.name
    intent_t = run_dir / "intent.timing.json"
    if intent_t.exists():
        t = json.loads(intent_t.read_text())
        timing["intent"] = {**t, "seconds": _seconds(t["start"], t["end"]), "by": "bob"}
    lens_times = {
        lens: json.loads((fdir / f"{lens}.timing.json").read_text())
        for lens in LENSES if (fdir / f"{lens}.timing.json").exists()
    }
    if lens_times:
        counts = {lens: min(len(v), MAX_PER_LENS) for lens, v in per_lens.items()}
        timing["attack"] = attack_timing(lens_times, counts)
    timing_path.write_text(json.dumps(timing, indent=2))

    missing = [f["id"] for f in merged if not (repo_root / f["test_path"]).exists()]
    print(f"merged {len(merged)} findings from {sorted(per_lens)} into {run_dir.name}/findings.json")
    if lens_times:
        a = timing["attack"]
        print(f"attack: {a['mode']}, {a['seconds']}s")
    if missing:
        print(f"missing test files (verifier will reject as 'test broken'): {missing}")
    return merged
