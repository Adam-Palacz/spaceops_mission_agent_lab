"""PS7.7 / BL-004 — Multi-cloud burst routing ADR and simulation tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from apps.llm_burst_routing import BurstRoutingSignals, decide_burst_route
from apps.llm_gateway import generate
from apps.llm_provenance import (
    capture_llm_provenance,
    reset_provenance_capture_for_tests,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ADR = REPO_ROOT / "docs" / "adr" / "0010-multicloud-burst-routing.md"
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "multicloud_burst_routing.md"
PS77 = (
    REPO_ROOT
    / "roadmap"
    / "02-production-scale"
    / "sprint-7"
    / "PS7.7-multicloud-burst-adr.md"
)
SIM_SCRIPT = REPO_ROOT / "scripts" / "simulate_multicloud_burst_routing.py"


@pytest.fixture(autouse=True)
def _reset_provenance():
    reset_provenance_capture_for_tests()
    yield
    reset_provenance_capture_for_tests()


def test_ps77_deliverables_exist() -> None:
    assert ADR.is_file()
    assert RUNBOOK.is_file()
    assert SIM_SCRIPT.is_file()
    text = PS77.read_text(encoding="utf-8")
    assert "| **Status** | Done |" in text
    assert "backend_routing_reason" in text


@pytest.mark.parametrize(
    ("name", "signals", "expected_reason", "expected_backend", "used_burst"),
    [
        (
            "kill_switch",
            BurstRoutingSignals(
                kill_switch=True,
                burst_enabled=True,
                primary_backend="openai",
                burst_backend="gpu",
                primary_healthy=True,
                burst_healthy=True,
                budget_ok=True,
                burst_within_cost_ceiling=True,
                burst_latency_p95_ms=100,
                latency_sla_ms=500,
            ),
            "kill_switch_active",
            "openai",
            False,
        ),
        (
            "burst_unavailable",
            BurstRoutingSignals(
                kill_switch=False,
                burst_enabled=True,
                primary_backend="openai",
                burst_backend="gpu",
                primary_healthy=True,
                burst_healthy=False,
                budget_ok=True,
                burst_within_cost_ceiling=True,
                burst_latency_p95_ms=100,
                latency_sla_ms=500,
            ),
            "burst_unavailable",
            "openai",
            False,
        ),
        (
            "burst_policy_match",
            BurstRoutingSignals(
                kill_switch=False,
                burst_enabled=True,
                primary_backend="openai",
                burst_backend="gpu",
                primary_healthy=True,
                burst_healthy=True,
                budget_ok=True,
                burst_within_cost_ceiling=True,
                burst_latency_p95_ms=120,
                latency_sla_ms=500,
            ),
            "burst_policy_match",
            "gpu",
            True,
        ),
    ],
)
def test_decide_burst_route_deterministic(
    name: str,
    signals: BurstRoutingSignals,
    expected_reason: str,
    expected_backend: str,
    used_burst: bool,
) -> None:
    del name
    a = decide_burst_route(signals)
    b = decide_burst_route(signals)
    assert a == b
    assert a.backend_routing_reason == expected_reason
    assert a.backend_to_use == expected_backend
    assert a.used_burst is used_burst


def test_simulation_script_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(SIM_SCRIPT)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_gateway_records_backend_routing_reason(monkeypatch) -> None:
    monkeypatch.setattr("config.settings.llm_budget_mode", "process")
    monkeypatch.setattr("config.settings.llm_daily_token_budget", 0)
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr("config.settings.llm_burst_kill_switch", False)
    monkeypatch.setattr("config.settings.llm_burst_routing_audit", True)
    monkeypatch.setattr("config.settings.llm_burst_enabled", False)
    monkeypatch.setattr(
        "apps.llm_gateway.get_backend_generator",
        lambda backend: (
            lambda **_: {
                "backend_actual": backend,
                "content": "ok",
                "usage": {"total_tokens": 1},
                "model_id": "gpt-4o-mini",
                "latency_ms": 1,
                "estimated_cost_usd": 0.0,
            }
        ),
    )

    with capture_llm_provenance() as buf:
        out = generate(prompt="audit", node="triage")

    assert out["backend_routing_reason"] == "configured:openai"
    assert buf[0]["backend_routing_reason"] == "configured:openai"


def test_kill_switch_audit_reason(monkeypatch) -> None:
    monkeypatch.setattr("config.settings.llm_budget_mode", "process")
    monkeypatch.setattr("config.settings.llm_daily_token_budget", 0)
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr("config.settings.llm_burst_kill_switch", True)
    monkeypatch.setattr("config.settings.llm_burst_routing_audit", True)
    monkeypatch.setattr(
        "apps.llm_gateway.get_backend_generator",
        lambda backend: (
            lambda **_: {
                "backend_actual": backend,
                "content": "ok",
                "usage": {"total_tokens": 1},
                "model_id": "gpt-4o-mini",
                "latency_ms": 1,
                "estimated_cost_usd": 0.0,
            }
        ),
    )

    out = generate(prompt="ks", node="decide")
    assert out["backend_routing_reason"] == "kill_switch_active"
