"""
PS4.4 — Deterministic semantic evals (fixtures, no LLM).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_semantic_cases_yaml_loads():
    from evals.semantic import load_semantic_cases

    cases = load_semantic_cases()
    assert len(cases) >= 7
    ids = {c["id"] for c in cases}
    assert "semantic-tool-empty-not-failure" in ids
    assert "semantic-citation-missing-refs" in ids


def test_semantic_suite_all_pass():
    from evals.semantic import run_semantic_suite

    code, summary = run_semantic_suite()
    assert code == 0
    assert summary["failed"] == 0
    assert summary["passed"] == summary["total"]


def test_empty_vs_tool_failure_distinction():
    """PS4.4 acceptance: empty telemetry is not tool_failure escalation."""
    from evals.semantic import load_fixture
    from evals.scoring import score_case

    case = {
        "must_escalate": False,
        "forbid_escalation_reason": "tool_failure",
        "expected_tool_outcomes": {"query_telemetry": "empty"},
    }
    result = load_fixture("tool_empty_not_failure.json")
    passed, failures = score_case(case, result)
    assert passed, failures

    fail_case = {
        "must_escalate": True,
        "expected_escalation_reason": "tool_failure",
        "expected_tool_outcomes": {"query_telemetry": "failure"},
    }
    tool_fail = load_fixture("tool_failure.json")
    passed2, _ = score_case(fail_case, tool_fail)
    assert passed2


def test_semantic_write_summary(tmp_path: Path):
    from evals.semantic import run_semantic_suite

    out = tmp_path / "semantic-summary.json"
    code, _ = run_semantic_suite(write_summary=out)
    assert code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["suite"] == "semantic_ps44"
    assert len(data["cases"]) >= 7
    assert all("case_id" in row for row in data["cases"])
