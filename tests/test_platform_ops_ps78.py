"""PS7.8 / BL-005 — Platform ops triage agent tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from apps.platform_ops.schema import SCHEMA_VERSION
from apps.platform_ops.triage import analyze_snapshot, build_triage_report

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "platform_ops"
PS78 = (
    REPO_ROOT
    / "roadmap"
    / "02-production-scale"
    / "sprint-7"
    / "PS7.8-platform-ops-triage-agent.md"
)
CLI = REPO_ROOT / "scripts" / "platform_ops_triage.py"
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "queue_dlq_recovery.md"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_ps78_deliverables_exist() -> None:
    assert PS78.is_file()
    assert CLI.is_file()
    assert (REPO_ROOT / "apps" / "platform_ops" / "collector.py").is_file()
    text = PS78.read_text(encoding="utf-8")
    assert "| **Status** | Done |" in text
    assert "platform_ops_triage" in RUNBOOK.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("fixture", "expected_class"),
    [
        ("postgres_down.json", "postgres_unavailable"),
        ("dlq_backlog.json", "dlq_backlog"),
        ("mcp_breaker_open.json", "mcp_breaker_open"),
    ],
)
def test_fixture_top_hypothesis_matches_class(
    fixture: str, expected_class: str
) -> None:
    snapshot = _load(fixture)
    analysis = analyze_snapshot(snapshot)
    assert analysis["top_hypothesis"]["class"] == expected_class


def test_triage_report_schema_stable() -> None:
    snapshot = _load("dlq_backlog.json")
    report = build_triage_report(snapshot, use_llm=False)
    assert report["schema_version"] == SCHEMA_VERSION
    assert report["snapshot"] == snapshot
    assert report["analysis"]["hypotheses"]
    assert report["audit"]["timestamp"]
    assert report["audit"]["write_actions_executed"] is False


def test_recommendations_include_safe_verify_before_risky() -> None:
    analysis = analyze_snapshot(_load("dlq_backlog.json"))
    recs = analysis["recommendations"]
    assert recs
    first_safe = next(r for r in recs if r["risk"] == "safe")
    assert first_safe["kind"] == "verify"
    risky = [r for r in recs if r["risk"] == "approval_required"]
    assert risky
    safe_idx = recs.index(first_safe)
    risky_idx = recs.index(risky[0])
    assert safe_idx < risky_idx


def test_apply_without_approval_fails() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--fixture",
            str(FIXTURES / "dlq_backlog.json"),
            "--apply",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "--i-approve" in (proc.stderr or proc.stdout)


def test_apply_with_approval_is_still_read_only_mvp() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--fixture",
            str(FIXTURES / "dlq_backlog.json"),
            "--apply",
            "--i-approve",
            "--no-llm",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "read-only" in proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["audit"]["write_actions_executed"] is False
    assert payload["analysis"]["apply_allowed"] is False


def test_collect_only_fixture_stdout() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--collect-only",
            "--fixture",
            str(FIXTURES / "mcp_breaker_open.json"),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["mcp"]["open_mcp_circuits"]
