#!/usr/bin/env python3
"""
PS4.7 — Aggregate GitHub Actions job results into a gate summary (hard vs soft).

Called from the gate-summary CI job with NEEDS_* env vars set in ci.yml.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.ci_gating import GateResult, GateReport, format_gate_summary  # noqa: E402

# job_key -> (gate_id, title, tier)
GITHUB_JOB_GATES: tuple[tuple[str, str, str, str], ...] = (
    ("lint", "lint-ruff", "Ruff + Mypy (lint job)", "hard"),
    ("golden-check", "golden-baseline", "Golden replay baseline", "hard"),
    ("safety-gates", "safety-opa-hitl", "OPA / HITL / guardrails tests", "hard"),
    ("test", "pytest-full", "Pytest full suite + migrations", "hard"),
    (
        "evals-hard",
        "evals-deterministic",
        "Must-escalate + citation + injection evals",
        "hard",
    ),
    ("evals-soft", "evals-full-suite", "Full eval suite (soft signal)", "soft"),
    ("docker-build", "docker-build", "Compose config + image build", "hard"),
)

RECOVERY = {
    "lint-ruff": "See lint job log; run `make lint` and `make typecheck`.",
    "golden-baseline": "Run `make golden-check`; update baselines only with confirm token.",
    "safety-opa-hitl": "Fix OPA/HITL/guardrail tests; see docs/runbooks/ci_gating_policy.md.",
    "pytest-full": "Run `make test` with Postgres; fix failing tests.",
    "evals-deterministic": "Run evals.scoring --case-id gates; ensure OPENAI_API_KEY in CI secrets.",
    "evals-full-suite": "Non-blocking; review full eval log and cases.yaml.",
    "docker-build": "Fix Dockerfile/compose; run `make compose-config` and `make docker-build`.",
}


def _job_result(job_key: str) -> str:
    return (
        os.environ.get(f"NEEDS_{job_key.upper().replace('-', '_')}_RESULT") or "skipped"
    ).lower()


def main() -> int:
    results: list[GateResult] = []
    hard_failed: list[str] = []
    soft_failed: list[str] = []

    for job_key, gate_id, title, tier in GITHUB_JOB_GATES:
        status = _job_result(job_key)
        passed = status == "success"
        if status == "skipped":
            passed = True
        results.append(
            GateResult(
                gate_id=gate_id,
                title=title,
                tier=tier,  # type: ignore[arg-type]
                passed=passed,
                exit_code=0 if passed else 1,
                recovery=RECOVERY.get(gate_id, "See job log in GitHub Actions."),
                output_tail=f"GitHub job `{job_key}` result: {status}",
            )
        )
        if not passed:
            if tier == "hard":
                hard_failed.append(gate_id)
            else:
                soft_failed.append(gate_id)

    report = GateReport(
        results=results, hard_failed=hard_failed, soft_failed=soft_failed
    )
    summary = format_gate_summary(report)
    print(summary)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        Path(summary_path).write_text(summary, encoding="utf-8")

    artifact = Path("ci-gate-summary.md")
    artifact.write_text(summary, encoding="utf-8")

    if report.blocking:
        print("\nCI GATE POLICY: HARD BLOCKER — merge blocked.", file=sys.stderr)
        return 1
    if report.soft_failed:
        print("\nCI GATE POLICY: soft signals present (non-blocking).")
    else:
        print("\nCI GATE POLICY: all gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
