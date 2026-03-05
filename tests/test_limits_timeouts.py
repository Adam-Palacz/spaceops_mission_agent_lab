"""
S1.12 NF6: Token/rate limits and timeouts — escalation on limit or timeout; no hang.
"""

from __future__ import annotations

import sys
from pathlib import Path
import time


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_run_exceeds_timeout_produces_escalation_packet(monkeypatch):
    """S1.12: Run that exceeds timeout produces escalation packet and does not hang."""
    # Make run timeout very small and LLM call artificially slow, without requiring OPENAI_API_KEY.
    monkeypatch.setattr("config.settings.agent_run_timeout_seconds", 0.1)
    from apps.agent import nodes

    def _slow_chat_completion(
        prompt: str, model: str = "gpt-4o-mini", temperature: float = 0
    ) -> tuple[str, int]:
        time.sleep(0.2)
        return "Power medium", 1

    monkeypatch.setattr(nodes, "_chat_completion", _slow_chat_completion)
    from apps.agent.graph import run_pipeline

    result = run_pipeline("timeout-test", {"ref": "test"})
    assert result.get("escalated") is True
    packet = result.get("escalation_packet") or {}
    assert packet.get("reason") == "run_timeout"
    assert result.get("report") is not None
    assert "run_timeout" in (result.get("report") or {}).get("executive_summary", "")


def test_run_exceeds_token_limit_produces_escalation_packet(monkeypatch):
    """S1.12: Run that exceeds token limit produces escalation packet."""
    # Enforce a very small token budget and stub LLM to consume more than that.
    monkeypatch.setattr("config.settings.agent_token_budget_per_run", 1)
    from apps.agent import nodes

    def _chat_completion_high_usage(
        prompt: str, model: str = "gpt-4o-mini", temperature: float = 0
    ) -> tuple[str, int]:
        return "Power medium", 10

    monkeypatch.setattr(nodes, "_chat_completion", _chat_completion_high_usage)
    from apps.agent.graph import run_pipeline

    result = run_pipeline("token-limit-test", {"ref": "test"})
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
    from apps.agent import nodes

    def _chat_completion_normal(
        prompt: str, model: str = "gpt-4o-mini", temperature: float = 0
    ) -> tuple[str, int]:
        # Reasonable token usage well under the generous budget
        return "Power medium", 50

    monkeypatch.setattr(nodes, "_chat_completion", _chat_completion_normal)
    from apps.agent.graph import run_pipeline

    result = run_pipeline("normal-limits-test", {"ref": "test"})
    # May still escalate for no_evidence if MCPs are down; we only assert no run_timeout/token_limit/llm_timeout
    packet = result.get("escalation_packet") or {}
    reason = packet.get("reason") or ""
    assert reason not in (
        "run_timeout",
        "token_limit",
        "rate_limit",
        "llm_timeout",
    ), "Normal run should not escalate due to limit/timeout"
