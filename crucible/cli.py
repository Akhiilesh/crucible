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
) -> None:
    """Run proof gates on all findings in a run directory."""
    from crucible.verify import run_verification
    run_verification(pr, base, Path(run_dir), _REPO_ROOT, keep)


@app.command()
def report(
    run_dir: str = typer.Option(..., help="Directory containing verdicts.json"),
) -> None:
    """Generate report.md and report.html from a completed verification run."""
    typer.echo("report: not implemented yet")


if __name__ == "__main__":
    app()
