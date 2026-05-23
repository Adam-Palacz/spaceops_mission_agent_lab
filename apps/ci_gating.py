"""
PS4.7 — CI gating policy: hard blockers vs soft signals, recovery hints, gate ordering.

Hard gates block merge/release. Soft gates report quality drift without failing the workflow
when CI runs with --soft (see evals.scoring and docs/runbooks/ci_gating_policy.md).
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Literal

GateTier = Literal["hard", "soft"]

# OPA fail-closed, approval/HITL, evidence, injection, output schema (PS4.7 matrix).
OPA_HITL_SAFETY_TEST_PATHS: tuple[str, ...] = (
    "tests/test_act_opa_policy.py",
    "tests/test_opa_client.py",
    "tests/test_evidence_policy_ps41.py",
    "tests/test_prompt_injection_ps43.py",
    "tests/test_guardrails_ps17.py",
    "tests/test_output_schema_ps42.py",
    "tests/test_behavior_metrics_ps46.py",
)

GOLDEN_TEST_PATHS: tuple[str, ...] = (
    "tests/test_golden_baseline.py",
    "tests/test_golden_runner_ps45.py",
)


@dataclass(frozen=True)
class Gate:
    gate_id: str
    title: str
    tier: GateTier
    command: list[str]
    recovery: str
    env: dict[str, str] = field(default_factory=dict)


def default_hard_gates() -> list[Gate]:
    """Ordered hard gates mirroring .github/workflows/ci.yml (deterministic first)."""
    py = sys.executable
    gates: list[Gate] = [
        Gate(
            gate_id="lint-ruff",
            title="Ruff lint",
            tier="hard",
            command=[py, "-m", "ruff", "check", "."],
            recovery="Run `ruff check .` locally; fix reported issues or `ruff check . --fix`.",
        ),
        Gate(
            gate_id="lint-mypy",
            title="Mypy typecheck",
            tier="hard",
            command=[
                py,
                "-m",
                "mypy",
                "-m",
                "apps.agent",
                "-m",
                "apps.api",
                "-m",
                "config",
                "-m",
                "evals",
                "--ignore-missing-imports",
            ],
            recovery="Run `make typecheck` or the mypy command from the CI log.",
        ),
        Gate(
            gate_id="golden-baseline",
            title="Golden replay baseline (PS4.5)",
            tier="hard",
            command=[py, "-m", "pytest", *GOLDEN_TEST_PATHS, "-q"],
            recovery="Run `make golden-check`. If intentional drift: `make golden-update RUN_ID=...` with confirm.",
        ),
        Gate(
            gate_id="safety-opa-hitl",
            title="OPA fail-closed + HITL/guardrails unit tests",
            tier="hard",
            command=[py, "-m", "pytest", *OPA_HITL_SAFETY_TEST_PATHS, "-q"],
            recovery=(
                "Inspect tests/test_act_opa_policy.py and related safety tests. "
                "OPA deny must escalate (policy_deny); restricted steps need approval when OPA allows."
            ),
        ),
        Gate(
            gate_id="eval-must-escalate",
            title="Eval: must-escalate-no-evidence (PS1.8)",
            tier="hard",
            command=[
                py,
                "-m",
                "evals.scoring",
                "--case-id",
                "must-escalate-no-evidence",
            ],
            recovery="Agent must escalate when no evidence; see evals/cases.yaml and check_escalation node.",
        ),
        Gate(
            gate_id="eval-citation-present",
            title="Eval: citation-present (PS1.8)",
            tier="hard",
            command=[py, "-m", "evals.scoring", "--case-id", "citation-present"],
            recovery="Run requires grounded citations; check Telemetry MCP and investigate node.",
        ),
        Gate(
            gate_id="eval-injection-suite",
            title="Eval: injection suite unsafe-action rate = 0 (S2.8)",
            tier="hard",
            command=[py, "-m", "evals.scoring", "--injection-only"],
            recovery="No unsafe plan/action phrases; see apps/agent/prompt_injection.py and evals/injection_suite/.",
        ),
    ]
    return gates


def default_soft_gates() -> list[Gate]:
    py = sys.executable
    return [
        Gate(
            gate_id="evals-full-suite",
            title="Full standard eval suite (quality signal)",
            tier="soft",
            command=[py, "-m", "evals.scoring", "--soft-signal"],
            recovery="Review failing case IDs in log; update cases.yaml or fix agent behavior. Non-blocking in CI.",
        ),
    ]


@dataclass
class GateResult:
    gate_id: str
    title: str
    tier: GateTier
    passed: bool
    exit_code: int
    recovery: str
    output_tail: str


@dataclass
class GateReport:
    results: list[GateResult]
    hard_failed: list[str]
    soft_failed: list[str]

    @property
    def blocking(self) -> bool:
        return len(self.hard_failed) > 0


def run_gate(gate: Gate, *, cwd: str | None = None) -> GateResult:
    env = {**os.environ, **gate.env}
    proc = subprocess.run(
        gate.command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    tail = "\n".join(combined.strip().splitlines()[-20:])
    return GateResult(
        gate_id=gate.gate_id,
        title=gate.title,
        tier=gate.tier,
        passed=proc.returncode == 0,
        exit_code=proc.returncode,
        recovery=gate.recovery,
        output_tail=tail,
    )


def run_gates(gates: list[Gate], *, cwd: str | None = None) -> tuple[int, GateReport]:
    results: list[GateResult] = []
    hard_failed: list[str] = []
    soft_failed: list[str] = []

    for gate in gates:
        result = run_gate(gate, cwd=cwd)
        results.append(result)
        if result.passed:
            continue
        if gate.tier == "hard":
            hard_failed.append(gate.gate_id)
        else:
            soft_failed.append(gate.gate_id)

    report = GateReport(
        results=results,
        hard_failed=hard_failed,
        soft_failed=soft_failed,
    )
    exit_code = 1 if report.blocking else 0
    return exit_code, report


def format_gate_summary(report: GateReport) -> str:
    lines = [
        "# CI gate summary (PS4.7)",
        "",
        "| Gate | Tier | Status | Recovery |",
        "|------|------|--------|----------|",
    ]
    for r in report.results:
        status = "PASS" if r.passed else "FAIL"
        recovery = r.recovery.replace("|", "\\|")[:120]
        lines.append(f"| {r.gate_id} | {r.tier} | {status} | {recovery} |")
    lines.append("")
    if report.hard_failed:
        lines.append(f"**HARD BLOCKERS:** {', '.join(report.hard_failed)}")
        lines.append("")
        lines.append("Merge/release is blocked until hard gates pass.")
    else:
        lines.append("**Hard gates:** all passed.")
    if report.soft_failed:
        lines.append("")
        lines.append(
            f"**SOFT SIGNALS (non-blocking):** {', '.join(report.soft_failed)}"
        )
        lines.append(
            "Review before release; does not fail CI when using soft eval job."
        )
    lines.append("")
    for r in report.results:
        if r.passed:
            continue
        lines.append(f"## Failed: {r.gate_id} ({r.title})")
        lines.append(f"- Exit code: {r.exit_code}")
        lines.append(f"- Recovery: {r.recovery}")
        if r.output_tail:
            lines.append("```")
            lines.append(r.output_tail)
            lines.append("```")
        lines.append("")
    return "\n".join(lines)
