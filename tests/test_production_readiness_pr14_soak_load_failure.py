"""PR1.4 — stage soak/load/failure pack tests."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "stage_pr14.py"
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "stage_soak_load_failure.md"
DEPLOY_RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "gcp_stage_deploy.md"
DOCS_INDEX = REPO_ROOT / "docs" / "README.md"
PORTFOLIO = REPO_ROOT / "docs" / "portfolio" / "README.md"
MAKEFILE = REPO_ROOT / "Makefile"
BOARD = REPO_ROOT / "roadmap" / "02.5-production-readiness" / "sprint-1" / "BOARD.md"
SPRINT_README = (
    REPO_ROOT / "roadmap" / "02.5-production-readiness" / "sprint-1" / "README.md"
)
SPRINT_REVIEW = (
    REPO_ROOT
    / "roadmap"
    / "02.5-production-readiness"
    / "sprint-1"
    / "SPRINT_REVIEW.md"
)
PR14 = (
    REPO_ROOT
    / "roadmap"
    / "02.5-production-readiness"
    / "sprint-1"
    / "PR1.4-soak-load-failure-tests.md"
)
PR14_REPORT = (
    REPO_ROOT
    / "roadmap"
    / "02.5-production-readiness"
    / "sprint-1"
    / "evidence"
    / "PR1.4-pilot-short-2026-06-23.json"
)


def _run_pr14(*args: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def test_pr14_script_dry_run_report_schema() -> None:
    report = _run_pr14("--profile", "dry-run", "--mode", "dry-run")
    assert report["schema_version"] == "pr14.stage-test-pack.v1"
    assert report["result"] == "pass"
    assert report["profile"]["name"] == "dry-run"
    assert report["acceptance_thresholds"]["api_run_p95_seconds"] == 60
    assert report["skipped_or_pending"][0]["item"] == "full_live_stage_profile"


def test_pr14_script_contains_required_failure_scenarios() -> None:
    report = _run_pr14("--profile", "pilot-short", "--mode", "plan")
    names = {scenario["name"] for scenario in report["failure_scenarios"]}
    assert {
        "api_pod_restart",
        "agent_worker_restart",
        "opa_unavailable",
        "postgres_restart",
        "queue_dlq_pressure",
        "llm_backend_failure",
        "budget_exhaustion",
    } <= names
    owners = {scenario["owner"] for scenario in report["failure_scenarios"]}
    assert {"platform", "mission-agent", "security", "data", "cost"} <= owners


def test_pr14_runbook_documents_profiles_thresholds_and_report() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    for required in (
        "pilot-short",
        "pilot-full",
        "70% Scenario A",
        "API run p95 latency: <= 60 seconds",
        "Run error rate: <= 5%",
        "F1",
        "F7",
        "Report requirements",
        "evidence is still required before PR1 closure",
        "failed live attempt on 2026-06-22",
        "preemptible single-node GKE",
        "terraform.pr14-stable.tfvars.example",
        "Current `--mode live` scope is limited",
        "does **not** automate the",
    ):
        assert required in text


def test_pr14_docs_makefile_board_and_spec_are_updated() -> None:
    assert "pr14-stage-test-pack" in MAKEFILE.read_text(encoding="utf-8")
    assert "stage_soak_load_failure.md" in DOCS_INDEX.read_text(encoding="utf-8")
    assert "stage_soak_load_failure.md" in PORTFOLIO.read_text(encoding="utf-8")
    assert "stage_soak_load_failure.md" in DEPLOY_RUNBOOK.read_text(encoding="utf-8")
    assert "terraform.pr14-stable.tfvars.example" in DEPLOY_RUNBOOK.read_text(
        encoding="utf-8"
    )
    assert "| PR1.4 | Soak, load, and failure test pack | Done |" in BOARD.read_text(
        encoding="utf-8"
    )
    pr_text = PR14.read_text(encoding="utf-8")
    assert "## Status\n\nDone" in pr_text
    assert "Live evidence attempt - 2026-06-22" in pr_text
    assert "Stable profile evidence - 2026-06-23" in pr_text
    assert "Final pilot-short closure run - 2026-06-23" in pr_text
    assert "Scenario A failed" in pr_text
    assert "PersistentVolume's node affinity" in pr_text
    assert "terraform.pr14-stable.tfvars.example" in pr_text
    assert "Prometheus `/api/v1/alerts` returned an empty alert list" in pr_text
    assert (
        "F1 API pod restart and F4 Postgres restart recovered successfully" in pr_text
    )
    assert "LLMBudgetExceededError" in pr_text
    assert "evidence/PR1.4-pilot-short-2026-06-23.json" in pr_text
    assert "Current `--mode live` scope is intentionally partial" in pr_text
    assert "[x] Soak/failure test results are attached" in SPRINT_README.read_text(
        encoding="utf-8"
    )
    assert "PR1.4 pilot-short report" in SPRINT_REVIEW.read_text(encoding="utf-8")


def test_pr14_live_report_records_done_evidence() -> None:
    report = json.loads(PR14_REPORT.read_text(encoding="utf-8"))
    assert report["schema_version"] == "pr14.stage-test-pack.v1"
    assert report["result"] == "pass"
    assert report["profile"]["name"] == "pilot-short"
    assert report["profile"]["actual_window"]["duration_minutes"] >= 30
    statuses = {
        scenario["id"]: scenario["status"] for scenario in report["failure_scenarios"]
    }
    assert statuses == {
        "F1": "pass",
        "F2": "not_applicable",
        "F3": "pass",
        "F4": "pass",
        "F5": "pass",
        "F6": "pass",
        "F7": "pass",
    }
    assert report["observability"]["prometheus_alerts_end_state"] == "[]"
    assert report["backlog_items"] == []


def test_pr14_local_markdown_links_resolve() -> None:
    for doc in (RUNBOOK, PR14, SPRINT_REVIEW):
        text = doc.read_text(encoding="utf-8")
        links = re.findall(r"\[[^\]]+\]\(([^)#][^)]+)\)", text)
        for href in links:
            target = href.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            assert (doc.parent / target).resolve().exists(), f"{doc}: {href}"
