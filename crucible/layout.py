"""
crucible/layout.py — Where the project under review keeps its code, tests and spec.

Read from an optional crucible.toml at the root of the repo being checked:

    [crucible]
    project_dir = "demo-app"          # pytest runs from here
    app_dir     = "demo-app/app"      # code the PR changes (used for the blame diff)
    tests_dir   = "demo-app/tests"    # proof tests are copied into <tests_dir>/crucible/
    spec_file   = "demo-app/spec/orders.md"   # numbered rules "R1: ..."

All paths are relative to the repo root. Missing keys fall back to the demo layout.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields, replace
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class Layout:
    project_dir: str = "demo-app"
    app_dir: str = "demo-app/app"
    tests_dir: str = "demo-app/tests"
    spec_file: str = "demo-app/spec/orders.md"

    @property
    def tests_in_project(self) -> str:
        """tests_dir relative to project_dir (the path pytest is given)."""
        return str(PurePosixPath(self.tests_dir).relative_to(self.project_dir))

    @property
    def spec_ref(self) -> str:
        """spec_file relative to project_dir, as cited in a finding's basis."""
        return str(PurePosixPath(self.spec_file).relative_to(self.project_dir))


DEFAULT_LAYOUT = Layout()


def load_layout(repo_root: Path, overrides: dict | None = None) -> Layout:
    """Layout from repo_root/crucible.toml, then non-empty overrides on top."""
    layout = DEFAULT_LAYOUT
    config = repo_root / "crucible.toml"
    if config.exists():
        section = tomllib.loads(config.read_text()).get("crucible", {})
        layout = replace(layout, **{f.name: section[f.name] for f in fields(Layout) if f.name in section})
    if overrides:
        layout = replace(layout, **{k: v for k, v in overrides.items() if v and k in {f.name for f in fields(Layout)}})
    return layout
