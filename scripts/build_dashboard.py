"""
scripts/build_dashboard.py — Build dashboard/index.html from runs/.

Embeds runs/summary.json and runs/*/verdicts.json into one self-contained page
(no external assets, light and dark mode). Run `crucible summary` first.

    .venv/bin/python scripts/build_dashboard.py
"""
from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    summary = json.loads((ROOT / "runs" / "summary.json").read_text())
    prs = []
    for p in summary["prs"]:
        run = ROOT / "runs" / p["pr"]
        verdicts = json.loads((run / "verdicts.json").read_text())
        prs.append({
            **p,
            "findings": [v for v in verdicts if v["verdict"] in ("PROVEN", "UNFIXED")],
            "noise": [v for v in verdicts if v["verdict"] == "REJECTED"],
            "report": f"../runs/{p['pr']}/report.html",
        })

    env = Environment(
        loader=FileSystemLoader(ROOT / "scripts"),
        autoescape=True, trim_blocks=True, lstrip_blocks=True,
    )
    html = env.get_template("dashboard.html.j2").render(
        prs=prs, totals=summary["totals"],
        summary_json=json.dumps(summary).replace("</", "<\\/"),
    )
    out = ROOT / "dashboard" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html)
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
