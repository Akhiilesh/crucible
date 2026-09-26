"""
crucible/gates.py — Pure gate logic for the Crucible proof-gate verifier.

All functions are pure: no file I/O, no subprocesses, no git calls.
Every gate returns (passed: bool, detail: str).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

# ── Constants ────────────────────────────────────────────────────────────────

UNIVERSAL_PROPERTIES: frozenset[str] = frozenset({
    "no_5xx",
    "no_unhandled_exception",
    "no_data_leak",
    "no_negative_money",
    "no_double_effect",
})

# pytest writes non-assertion exceptions as <failure> too, so we must
# distinguish assertion failures from all other exceptions by inspecting
# the failure message/text.
_ASSERTION_PREFIXES = ("assert", "assertionerror")


# ── JUnit parsing ─────────────────────────────────────────────────────────────

def parse_junit(junit_xml: str) -> str:
    """Parse a JUnit XML string and return the outcome for this run.

    Returns one of:
      "failure"  — at least one <failure> that is an assertion error, no <error>s
      "error"    — <error> present, zero testcases, unparseable XML, missing file,
                   or a <failure> whose message is not an assertion error
      "passed"   — all testcases passed
      "skipped"  — at least one <skipped>, no failures or errors

    "timeout" is never produced here; the runner sets it when the process
    times out before producing a JUnit file.
    """
    if not junit_xml or not junit_xml.strip():
        return "error"

    try:
        root = ET.fromstring(junit_xml)
    except ET.ParseError:
        return "error"

    # Collect all testcase elements across nested suites
    testcases = root.findall(".//testcase")
    if not testcases:
        return "error"

    has_error = any(tc.find("error") is not None for tc in testcases)
    if has_error:
        return "error"

    failure_elements = [tc.find("failure") for tc in testcases]
    failure_elements = [f for f in failure_elements if f is not None]

    if failure_elements:
        # Every failure must be an assertion; any other exception → "error"
        for f in failure_elements:
            msg = (f.get("message") or f.text or "").strip().lower()
            if not any(msg.startswith(p) for p in _ASSERTION_PREFIXES):
                return "error"
        return "failure"

    skipped = any(tc.find("skipped") is not None for tc in testcases)
    if skipped:
        return "skipped"

    return "passed"


# ── Gate G4 — Grounded ────────────────────────────────────────────────────────

def gate_g4_grounded(
    basis: str,
    spec_text: str,
    intent_rule_ids: set[str] | None = None,
) -> tuple[bool, str]:
    """Static grounding check. Runs before any pytest subprocess.

    Accepts:
      - A value in UNIVERSAL_PROPERTIES
      - "spec/orders.md#R<n>" where "R<n>:" appears in spec_text and, when
        intent_rule_ids is given (the run has an intent.json), R<n> is listed there

    Returns (True, "") or (False, "ungrounded").
    """
    if basis in UNIVERSAL_PROPERTIES:
        return True, ""

    m = re.fullmatch(r"spec/orders\.md#(R\d+)", basis)
    if m:
        rule_id = m.group(1)
        in_spec = re.search(rf"^{re.escape(rule_id)}:", spec_text, re.MULTILINE)
        in_intent = intent_rule_ids is None or rule_id in intent_rule_ids
        if in_spec and in_intent:
            return True, ""

    return False, "ungrounded"


# ── Gate G1 — Fails on PR ────────────────────────────────────────────────────

def gate_g1_fails_on_pr(outcome: str) -> tuple[bool, str]:
    """Check that the test fails on the PR branch with an assertion error.

    Returns (True, "") or (False, <reason>).
    """
    if outcome == "failure":
        return True, ""
    if outcome == "passed":
        return False, "does not fail on PR"
    # "error", "timeout", "skipped" all mean the test itself is broken
    return False, "test broken"


# ── Gate G3 — Reproducible ───────────────────────────────────────────────────

def gate_g3_reproducible(outcomes: list[str]) -> tuple[bool, str]:
    """Require that all 3 PR runs produce "failure".

    outcomes must be a list of exactly 3 strings (G1 run + 2 more).
    Returns (passed, repro_string) where repro_string is always "k/3".
    """
    k = sum(1 for o in outcomes if o == "failure")
    repro = f"{k}/3"
    if k == 3:
        return True, repro
    return False, repro


# ── After-fix check ───────────────────────────────────────────────────────────

def after_fix_status(outcomes: list[str]) -> tuple[bool, str]:
    """A fixed proof test must pass on every fresh run.

    outcomes is a list of parse_junit results from runs on the fixed PR branch.
    Returns (all_passed, "k/n") where k counts "passed".
    """
    k = sum(1 for o in outcomes if o == "passed")
    return k == len(outcomes) and k > 0, f"{k}/{len(outcomes)}"


# ── Diff analysis helpers (used by G2) ───────────────────────────────────────

def extract_added_routes(diff_text: str) -> list[str]:
    """Scan added lines (+, not +++) for @app.<method>("<path>") decorators.

    Returns a list of path strings, e.g. ["/orders/{order_id}/refund"].
    """
    routes: list[str] = []
    pattern = re.compile(r'^\+(?!\+\+).*@app\.\w+\(\s*["\']([^"\']+)["\']')
    for line in diff_text.splitlines():
        m = pattern.match(line)
        if m:
            routes.append(m.group(1))
    return routes


def route_to_regex(route_template: str) -> re.Pattern[str]:
    """Convert a FastAPI route template to an anchored regex.

    {param} becomes [^/]+ so "/orders/{order_id}/refund" matches
    "/orders/o1/refund" or "/orders/abc-123/refund".
    """
    escaped = re.escape(route_template)
    # re.escape turns { } into \{ \}; replace \{...\} with [^/]+
    pattern = re.sub(r"\\\{[^}]+\\\}", r"[^/]+", escaped)
    return re.compile(f"^{pattern}$")


def extract_added_functions(diff_text: str) -> list[str]:
    """Scan added lines for def/async def/class declarations.

    Returns a list of names (functions and classes added by the PR).
    Only lines in demo-app/app are considered (diff is already filtered to
    demo-app/app by the caller, but this function is pure so it accepts any
    diff text).
    """
    names: list[str] = []
    pattern = re.compile(
        r'^\+(?!\+\+)\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)'
    )
    for line in diff_text.splitlines():
        m = pattern.match(line)
        if m:
            names.append(m.group(1))
    return names


def normalise_url_segments(test_source: str) -> list[str]:
    """Extract URL-like strings from test source, normalising f-string expressions.

    Finds strings that:
      - Start with "/"
      - Contain at least one more path segment
    Replaces {expr} f-string slots with a literal "<seg>" placeholder so they
    can be matched against route_to_regex patterns.

    Returns a flat list of normalised path strings.
    """
    # Match both plain strings and f-strings that look like paths
    raw_pattern = re.compile(r'[fF]?["\'](\s*/[^"\']+)["\']')
    results: list[str] = []
    for m in raw_pattern.finditer(test_source):
        path = m.group(1).strip()
        # Normalise {expr} → a dummy segment that won't break the regex match
        normalised = re.sub(r"\{[^}]+\}", "PLACEHOLDER", path)
        results.append(normalised)
    return results


# ── Gate G2 — Blame ───────────────────────────────────────────────────────────

def gate_g2_blame(
    base_outcome: str,
    diff_text: str,
    test_source: str,
) -> tuple[bool, str]:
    """Determine whether the PR caused the failure or it pre-existed.

    base_outcome: parse_junit result for the base worktree run.
    diff_text:    output of `git diff <base>...<pr> -- demo-app/app` (app code only).
    test_source:  raw text of the proof test file.

    Logic:
      - base "passed"  → (True, "passes_on_base")
      - any other base outcome → new-code check:
          * extract added routes and functions from diff_text
          * normalise URLs from test_source
          * if any URL matches an added route regex → (True, "new_code")
          * if test_source contains any added function/class name as a word → (True, "new_code")
          * else → (False, "pre-existing behaviour")
    """
    if base_outcome == "passed":
        return True, "passes_on_base"

    added_routes = extract_added_routes(diff_text)
    added_names = extract_added_functions(diff_text)
    url_candidates = normalise_url_segments(test_source)

    # Check route matches
    for route in added_routes:
        rx = route_to_regex(route)
        for url in url_candidates:
            if rx.match(url):
                return True, "new_code"

    # Check function/class name references (word boundaries)
    for name in added_names:
        if re.search(rf"\b{re.escape(name)}\b", test_source):
            return True, "new_code"

    return False, "pre_existing"
