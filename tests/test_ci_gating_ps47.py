"""
PS4.7 — CI gating policy: hard vs soft gates, OPA/HITL path, gate runner behavior.
"""

from __future__ import annotations

import sys

from apps.ci_gating import (
    OPA_HITL_SAFETY_TEST_PATHS,
    Gate,
    default_hard_gates,
    format_gate_summary,
    run_gates,
)


def test_hard_gate_registry_includes_opa_hitl_and_evals():
    gates = {g.gate_id: g for g in default_hard_gates()}
    assert "safety-opa-hitl" in gates
    assert gates["safety-opa-hitl"].tier == "hard"
    assert "eval-must-escalate" in gates
    assert "eval-citation-present" in gates
    assert "eval-injection-suite" in gates
    cmd = gates["safety-opa-hitl"].command
    assert "pytest" in cmd
    for path in OPA_HITL_SAFETY_TEST_PATHS:
        assert path in cmd


def test_simulated_safety_regression_fails_hard_gate():
    failing = Gate(
        gate_id="simulate-safety-regression",
        title="Simulated OPA regression",
        tier="hard",
        command=[sys.executable, "-c", "import sys; sys.exit(1)"],
        recovery="Restore OPA fail-closed behavior in act node.",
    )
    exit_code, report = run_gates([failing])
    assert exit_code == 1
    assert report.blocking is True
    assert "simulate-safety-regression" in report.hard_failed
    summary = format_gate_summary(report)
    assert "HARD BLOCKERS" in summary
    assert "Restore OPA fail-closed" in summary


def test_soft_gate_failure_does_not_block():
    soft_fail = Gate(
        gate_id="simulate-quality-drift",
        title="Simulated eval drift",
        tier="soft",
        command=[sys.executable, "-c", "import sys; sys.exit(1)"],
        recovery="Review eval cases; non-blocking.",
    )
    exit_code, report = run_gates([soft_fail])
    assert exit_code == 0
    assert not report.blocking
    assert "simulate-quality-drift" in report.soft_failed
    summary = format_gate_summary(report)
    assert "SOFT SIGNALS" in summary


def test_mixed_hard_and_soft_only_hard_blocks():
    gates = [
        Gate(
            gate_id="ok-hard",
            title="ok",
            tier="hard",
            command=[sys.executable, "-c", "import sys; sys.exit(0)"],
            recovery="n/a",
        ),
        Gate(
            gate_id="bad-soft",
            title="soft",
            tier="soft",
            command=[sys.executable, "-c", "import sys; sys.exit(2)"],
            recovery="review",
        ),
    ]
    exit_code, report = run_gates(gates)
    assert exit_code == 0
    assert report.hard_failed == []
    assert report.soft_failed == ["bad-soft"]
