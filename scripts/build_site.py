"""
scripts/build_site.py — Build the static showcase site in site/ for Vercel.

Read-only: the landing page (upload panel replaced by "Try it yourself"), the results
dashboard, the three PR reports and the demo repo zip. Every number comes from runs/.

    .venv/bin/python -m crucible.cli summary
    .venv/bin/python scripts/build_dashboard.py
    .venv/bin/python scripts/build_site.py --repo-url https://github.com/<user>/crucible
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PRS = ("pr-1-refunds", "pr-2-discounts", "pr-3-bulk-cancel")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-url", default="", help="Public GitHub URL shown on the site")
    args = parser.parse_args()

    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()

    totals = json.loads((ROOT / "runs" / "summary.json").read_text())["totals"]
    env = Environment(loader=FileSystemLoader(ROOT / "crucible" / "templates"), autoescape=True)
    html = env.get_template("studio.html.j2").render(totals=totals, static=True, repo_url=args.repo_url)
    (SITE / "index.html").write_text(html)

    (SITE / "dashboard").mkdir()
    shutil.copy(ROOT / "dashboard" / "index.html", SITE / "dashboard" / "index.html")
    for pr in PRS:
        (SITE / "runs" / pr).mkdir(parents=True)
        shutil.copy(ROOT / "runs" / pr / "report.html", SITE / "runs" / pr / "report.html")
    (SITE / "examples").mkdir()
    shutil.copy(ROOT / "examples" / "orders-service-demo.zip", SITE / "examples")

    for f in sorted(SITE.rglob("*")):
        if f.is_file():
            print(f"  {f.relative_to(ROOT)}  ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
