"""
S1.12 NF6: Token/rate limits and timeouts — escalation on limit or timeout; no hang.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_run_exceeds_timeout_produces_escalation_packet(monkeypatch):
    """S1.12: Run that exceeds timeout produces escalation packet and does not hang."""
    monkeypatch.setattr("config.settings.agent_run_timeout_seconds", 1)
    # Pipeline normally takes many seconds (LLM + MCP); 1s should timeout
    from apps.agent.graph import run_pipeline
    try:
        result = run_pipeline("timeout-test", {"ref": "test"})
    except Exception as e:
        if "OPENAI_API_KEY" in str(e):
            pytest.skip("OPENAI_API_KEY not set")
        raise
    assert result.get("escalated") is True
    packet = result.get("escalation_packet") or {}
    assert packet.get("reason") == "run_timeout"
    assert result.get("report") is not None
    assert "run_timeout" in (result.get("report") or {}).get("executive_summary", "")


def test_run_exceeds_token_limit_produces_escalation_packet(monkeypatch):
    """S1.12: Run that exceeds token limit produces escalation packet."""
    monkeypatch.setattr("config.settings.agent_token_budget_per_run", 1)
    from apps.agent.graph import run_pipeline
    try:
        result = run_pipeline("token-limit-test", {"ref": "test"})
    except Exception as e:
        if "OPENAI_API_KEY" in str(e):
            pytest.skip("OPENAI_API_KEY not set")
        raise
    assert result.get("escalated") is True
    packet = result.get("escalation_packet") or {}
    assert packet.get("reason") == "token_limit"


def test_run_exceeds_rate_limit_produces_escalation_packet(monkeypatch):
    """S1.12: When max LLM calls per run is reached, decide escalates with reason rate_limit (no extra LLM call)."""
    monkeypatch.setattr("config.settings.agent_max_llm_calls_per_run", 1)
    from apps.agent.nodes import decide
    from apps.agent.state import AgentState
    # State after triage (1 LLM call used) with evidence so check_escalation would not escalate
    state: AgentState = {
        "incident_id": "rate-limit-test",
        "subsystem": "Power",
        "risk": "medium",
        "hypotheses": ["Telemetry: 2 samples.", "Runbook: power bus procedure."],
        "citations": [{"doc_id": "rb1", "snippet_id": "s1", "content": "..."}],
        "llm_calls_used": 1,
        "tokens_used": 100,
    }
    result = decide(state)
    assert result.get("escalated") is True
    packet = result.get("escalation_packet") or {}
    assert packet.get("reason") == "rate_limit"


def test_normal_run_under_limits_completes_without_false_escalation(monkeypatch):
    """S1.12: Normal run under limits completes without false escalation (no timeout/limit trigger)."""
    monkeypatch.setattr("config.settings.agent_run_timeout_seconds", 300)
    monkeypatch.setattr("config.settings.agent_token_budget_per_run", 100_000)
    from apps.agent.graph import run_pipeline
    try:
        result = run_pipeline("normal-limits-test", {"ref": "test"})
    except Exception as e:
        if "OPENAI_API_KEY" in str(e):
            pytest.skip("OPENAI_API_KEY not set")
        raise
    # May still escalate for no_evidence if MCPs are down; we only assert no run_timeout/token_limit
    packet = result.get("escalation_packet") or {}
    reason = packet.get("reason") or ""
    assert reason not in ("run_timeout", "token_limit", "rate_limit", "llm_timeout"), (
        "Normal run should not escalate due to limit/timeout"
    )
