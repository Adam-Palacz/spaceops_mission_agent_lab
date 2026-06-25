#!/usr/bin/env python3
"""PR1.4 stage soak/load/failure test pack planner and dry-run reporter."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NAMESPACE = "spaceops-stage"


@dataclass(frozen=True)
class Profile:
    name: str
    duration_minutes: int
    run_interval_seconds: int
    max_concurrent_runs: int
    ingest_lines_per_minute: int
    fixture_mix: dict[str, int]


PROFILES = {
    "dry-run": Profile(
        name="dry-run",
        duration_minutes=0,
        run_interval_seconds=0,
        max_concurrent_runs=0,
        ingest_lines_per_minute=0,
        fixture_mix={"plan_validation": 100},
    ),
    "pilot-short": Profile(
        name="pilot-short",
        duration_minutes=30,
        run_interval_seconds=120,
        max_concurrent_runs=3,
        ingest_lines_per_minute=100,
        fixture_mix={"scenario_a": 70, "scenario_b": 20, "ingest_only": 10},
    ),
    "pilot-full": Profile(
        name="pilot-full",
        duration_minutes=120,
        run_interval_seconds=120,
        max_concurrent_runs=5,
        ingest_lines_per_minute=250,
        fixture_mix={"scenario_a": 70, "scenario_b": 20, "ingest_only": 10},
    ),
}

ACCEPTANCE_THRESHOLDS: dict[str, Any] = {
    "api_availability_pilot_short": "100%",
    "api_availability_pilot_full": ">=99%",
    "api_run_p95_seconds": 60,
    "run_error_rate_max": "5%",
    "scenario_a": "report plus evidence after recovery",
    "scenario_b": "escalation packet",
    "fail_closed": ["opa_unavailable", "llm_backend_failure", "budget_exhaustion"],
    "prometheus_targets": "all PR1.1 targets recover to UP",
    "page_alerts_end_state": "none firing outside intentional failure window",
}

FAILURE_SCENARIOS: list[dict[str, str]] = [
    {
        "id": "F1",
        "name": "api_pod_restart",
        "command": "kubectl rollout restart deploy/spaceops-api -n {namespace}",
        "restore": "kubectl rollout status deploy/spaceops-api -n {namespace} --timeout=3m",
        "expected": "API /health recovers and scenario A/B still pass.",
        "owner": "platform",
    },
    {
        "id": "F2",
        "name": "agent_worker_restart",
        "command": (
            "kubectl delete pod -n {namespace} "
            "-l app.kubernetes.io/component=agent-worker --wait=false"
        ),
        "restore": (
            "kubectl rollout status deploy/spaceops-agent-worker "
            "-n {namespace} --timeout=3m"
        ),
        "expected": "Variant A worker lease is reclaimed; Variant B records N/A.",
        "owner": "mission-agent",
    },
    {
        "id": "F3",
        "name": "opa_unavailable",
        "command": "kubectl scale deploy/spaceops-opa -n {namespace} --replicas=0",
        "restore": (
            "kubectl scale deploy/spaceops-opa -n {namespace} --replicas=1 && "
            "kubectl rollout status deploy/spaceops-opa -n {namespace} --timeout=3m"
        ),
        "expected": "Restricted action fails closed; OPA failure metric/alert is visible.",
        "owner": "security",
    },
    {
        "id": "F4",
        "name": "postgres_restart",
        "command": "kubectl rollout restart statefulset/spaceops-postgres -n {namespace}",
        "restore": (
            "kubectl rollout status statefulset/spaceops-postgres "
            "-n {namespace} --timeout=5m"
        ),
        "expected": "API recovers; schema and evidence data remain intact.",
        "owner": "data",
    },
    {
        "id": "F5",
        "name": "queue_dlq_pressure",
        "command": 'make gcp-stage-demo GCP_STAGE_ARGS="--scenario both"',
        "restore": "inspect DLQ and run queue_dlq_recovery.md if backlog remains",
        "expected": "No unbounded DLQ growth; backlog drains or has owner.",
        "owner": "platform",
    },
    {
        "id": "F6",
        "name": "llm_backend_failure",
        "command": "deploy throwaway overlay with invalid LLM endpoint, then run scenario A",
        "restore": 'make gcp-stage-deploy GCP_STAGE_DEPLOY_ARGS="--monitoring"',
        "expected": "Run escalates with provider/tool failure and no unsafe action.",
        "owner": "mission-agent",
    },
    {
        "id": "F7",
        "name": "budget_exhaustion",
        "command": "deploy throwaway overlay with LLM_DAILY_TOKEN_BUDGET=1",
        "restore": 'make gcp-stage-deploy GCP_STAGE_DEPLOY_ARGS="--monitoring"',
        "expected": "Run escalates with budget_exceeded and no backend fallback.",
        "owner": "cost",
    },
]


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def format_command(template: str, namespace: str) -> str:
    return template.format(namespace=namespace)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    profile = PROFILES[args.profile]
    namespace = args.namespace
    project = args.project or os.getenv("GCP_PROJECT_ID", "")
    mode = args.mode
    command_plan = [
        'make gcp-stage-up GCP_STAGE_DEPLOY_ARGS="--monitoring"',
        f"scripts/stage_pr14.py --profile {profile.name} --mode live",
        "make gcp-stage-down",
    ]
    scenarios = [
        {
            **scenario,
            "command": format_command(scenario["command"], namespace),
            "restore": format_command(scenario["restore"], namespace),
            "status": "planned"
            if mode == "plan"
            else "dry-run"
            if mode == "dry-run"
            else "pending",
        }
        for scenario in FAILURE_SCENARIOS
    ]
    skipped = []
    if mode != "live":
        skipped.append(
            {
                "item": "full_live_stage_profile",
                "reason": "CI-safe mode; live GKE execution requires --mode live in a time-boxed stage window",
                "owner": "platform",
                "target": "before PR1 closure / production-pilot go-no-go",
            }
        )
    return {
        "schema_version": "pr14.stage-test-pack.v1",
        "generated_at": _now(),
        "mode": mode,
        "profile": asdict(profile),
        "operator": args.operator or os.getenv("USERNAME") or os.getenv("USER") or "",
        "project": project,
        "namespace": namespace,
        "api_url": args.api_url or os.getenv("GCP_API_URL", ""),
        "command_plan": command_plan,
        "acceptance_thresholds": ACCEPTANCE_THRESHOLDS,
        "failure_scenarios": scenarios,
        "observability_checks": [
            "Prometheus /api/v1/targets has PR1.1 targets UP",
            "Prometheus /api/v1/rules includes spaceops.slo.rules",
            "Prometheus /api/v1/alerts has no page alert firing at end",
            "Grafana SpaceOps Production Readiness SLO board reviewed",
        ],
        "backlog_policy": (
            "Every failed or skipped required live scenario must become a backlog/task item "
            "with owner before PR1 closure."
        ),
        "skipped_or_pending": skipped,
        "result": "pass"
        if mode == "dry-run"
        else "planned"
        if mode == "plan"
        else "pending_live_execution",
    }


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run_live(report: dict[str, Any]) -> dict[str, Any]:
    if not report.get("api_url"):
        raise SystemExit("--api-url or GCP_API_URL is required for --mode live")
    commands = [
        ["make", "gcp-stage-smoke"],
        ["make", "gcp-stage-demo"],
    ]
    executed: list[dict[str, Any]] = []
    for cmd in commands:
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), check=False, text=True)
        executed.append({"command": cmd, "returncode": proc.returncode})
        if proc.returncode != 0:
            report["result"] = "failed"
            report["executed_commands"] = executed
            return report
    report["result"] = "pending_failure_scenarios"
    report["executed_commands"] = executed
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="dry-run")
    parser.add_argument(
        "--mode", choices=("dry-run", "plan", "live"), default="dry-run"
    )
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    parser.add_argument("--project", default="")
    parser.add_argument("--api-url", default="")
    parser.add_argument("--operator", default="")
    parser.add_argument("--write-report", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = build_report(args)
    if args.mode == "live":
        report = run_live(report)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.write_report:
        write_report(report, args.write_report)
    return (
        0 if report["result"] in {"pass", "planned", "pending_failure_scenarios"} else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
