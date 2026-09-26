"""Crucible CLI — proof-carrying code review."""
from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(
    name="crucible",
    help="Crucible: prove bugs with failing tests, then fix them.",
    no_args_is_help=True,
)

# Repo root is two levels up from this file: crucible/crucible/cli.py → crucible/
_REPO_ROOT = Path(__file__).resolve().parent.parent


@app.command()
def verify(
    pr: str = typer.Option(..., help="PR branch name to verify"),
    base: str = typer.Option("main", help="Base branch to compare against"),
    run_dir: str = typer.Option(..., help="Directory containing findings.json and test files"),
    keep: bool = typer.Option(False, help="Keep git worktrees after verification"),
    after_fix: bool = typer.Option(
        False, "--after-fix",
        help="Re-run PROVEN proof tests on the fixed PR branch; they must now pass",
    ),
) -> None:
    """Run proof gates on all findings in a run directory."""
    if after_fix:
        from crucible.verify import run_after_fix_check
        run_after_fix_check(pr, Path(run_dir), _REPO_ROOT, keep)
        return
    from crucible.verify import run_verification
    run_verification(pr, base, Path(run_dir), _REPO_ROOT, keep)


@app.command()
def merge(
    run_dir: str = typer.Option(..., help="Run directory containing findings/<lens>.json"),
) -> None:
    """Merge per-lens attacker findings into findings.json and record attack timing."""
    from crucible.merge import run_merge
    run_merge(Path(run_dir), _REPO_ROOT)


@app.command()
def report(
    run_dir: str = typer.Option(..., help="Directory containing verdicts.json"),
    base: str = typer.Option("main", help="Base branch the spec is read from"),
) -> None:
    """Generate report.md and report.html from a completed verification run."""
    from crucible.report import build_report
    md_path, html_path = build_report(Path(run_dir), _REPO_ROOT, base)
    typer.echo(f"wrote {md_path.relative_to(_REPO_ROOT)} and {html_path.relative_to(_REPO_ROOT)}")


@app.command()
def summary(
    runs_dir: str = typer.Option("runs", help="Directory containing one run dir per PR"),
) -> None:
    """Write runs/summary.json and runs/summary.md across all PR runs."""
    from crucible.summary import run_summary
    path = Path(runs_dir)
    run_summary(path if path.is_absolute() else _REPO_ROOT / path)
    typer.echo(f"wrote {runs_dir}/summary.json and {runs_dir}/summary.md")


if __name__ == "__main__":
    app()
