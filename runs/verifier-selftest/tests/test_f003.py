"""F-003 — Fake: broken test — module-level import of nonexistent module.

The import fails at collection time; pytest produces an <error> (collection
error) in the JUnit output. G1 classifies this as "test broken".
"""
from __future__ import annotations

import app.nonexistent_module  # noqa: F401 — intentionally broken import


def test_placeholder(alice_client):
    assert True
