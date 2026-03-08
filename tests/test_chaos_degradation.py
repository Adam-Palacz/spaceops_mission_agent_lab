"""
S3.5 — Chaos / degradation test harness.

Simulates failures or slowdowns in key dependencies (MCP, OPA) and asserts
the agent fails closed or escalates; no hang, no unsafe action.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from apps.agent.nodes import act, investigate
from apps.agent.state import AgentState


def _investigate_state(
    incident_id: str = "chaos-inc",
    trace_id: str | None = None,
    payload: dict | None = None,
) -> AgentState:
    return {
        "incident_id": incident_id,
        "trace_id": trace_id or incident_id,
        "payload": payload
        or {
            "time_range_start": "2025-02-14T09:00:00Z",
            "time_range_end": "2025-02-14T11:00:00Z",
        },
        "subsystem": "Power",
    }


def _act_state(
    plan: list[dict[str, Any]], incident_id: str = "chaos-act"
) -> AgentState:
    return {
        "incident_id": incident_id,
        "trace_id": incident_id,
        "plan": plan,
        "act_results": [],
        "approval_requests": [],
    }


# --- Scenario 1: Telemetry MCP very slow or 5xx ---


def test_chaos_telemetry_mcp_timeout_investigate_completes_no_hang(monkeypatch):
    """
    S3.5 Chaos scenario: Telemetry MCP times out.
    Expected: investigate completes (no hang), returns fallback hypothesis; no exception.
    """

    def _timeout(*args: Any, **kwargs: Any) -> list:
        raise httpx.TimeoutException("telemetry timeout")

    monkeypatch.setattr("apps.agent.nodes.call_telemetry", _timeout)
    # KB can return empty so we don't need to patch it for this scenario
    monkeypatch.setattr("apps.agent.nodes.call_search_runbooks", lambda q, limit=5: [])
    monkeypatch.setattr(
        "apps.agent.nodes.call_search_postmortems", lambda sig, limit=5: []
    )

    state = _investigate_state()
    out = investigate(state)

    hypotheses = out.get("hypotheses") or []
    assert any("No telemetry or KB hits" in (h or "") for h in hypotheses)
    assert "hypotheses" in out and "citations" in out


def test_chaos_telemetry_mcp_5xx_investigate_completes_no_hang(monkeypatch):
    """
    S3.5 Chaos scenario: Telemetry MCP returns 5xx (simulated via exception).
    Expected: investigate completes with empty telemetry, fallback hypothesis.
    """

    def _server_error(*args: Any, **kwargs: Any) -> list:
        # Simulate 5xx: any exception leads to empty telemetry in investigate
        resp = MagicMock()
        resp.status_code = 500
        raise httpx.HTTPStatusError("500", request=MagicMock(), response=resp)

    monkeypatch.setattr("apps.agent.nodes.call_telemetry", _server_error)
    monkeypatch.setattr("apps.agent.nodes.call_search_runbooks", lambda q, limit=5: [])
    monkeypatch.setattr(
        "apps.agent.nodes.call_search_postmortems", lambda sig, limit=5: []
    )

    state = _investigate_state()
    out = investigate(state)

    hypotheses = out.get("hypotheses") or []
    assert any("No telemetry or KB hits" in (h or "") for h in hypotheses)


# --- Scenario 2: KB MCP unavailable ---


def test_chaos_kb_mcp_unavailable_investigate_completes_no_hang(monkeypatch):
    """
    S3.5 Chaos scenario: KB MCP (runbooks) unavailable.
    Expected: investigate completes; telemetry can be empty, fallback hypothesis present.
    """

    def _kb_unavailable(*args: Any, **kwargs: Any) -> list:
        raise httpx.ConnectError("KB unreachable")

    monkeypatch.setattr("apps.agent.nodes.call_telemetry", lambda *a, **k: [])
    monkeypatch.setattr("apps.agent.nodes.call_search_runbooks", _kb_unavailable)
    monkeypatch.setattr(
        "apps.agent.nodes.call_search_postmortems", lambda sig, limit=5: []
    )

    state = _investigate_state()
    out = investigate(state)

    hypotheses = out.get("hypotheses") or []
    assert any("No telemetry or KB hits" in (h or "") for h in hypotheses)
    assert "citations" in out


# --- Scenario 3: OPA unavailable or timing out ---


def test_chaos_opa_unavailable_act_escalates_fail_closed(monkeypatch):
    """
    S3.5 Chaos scenario: OPA unavailable or timing out (opa_allow returns False).
    Expected: Act escalates with policy_deny; no approval request; no unsafe action.
    """
    monkeypatch.setattr("apps.agent.nodes.opa_allow", lambda step, inc: False)
    monkeypatch.setattr(
        "apps.agent.nodes.approval_store_create",
        lambda **kw: pytest.fail(
            "approval_store_create must not be called when OPA denies"
        ),
    )

    state = _act_state(
        plan=[
            {
                "safe": False,
                "action_type": "change_config",
                "action": "Adjust threshold",
                "doc_ids": ["rb-1"],
                "snippet_ids": [],
            }
        ],
    )
    result = act(state)

    assert result.get("escalated") is True
    packet = result.get("escalation_packet") or {}
    assert packet.get("reason") == "policy_deny"
    assert (result.get("approval_requests") or []) == []


def test_chaos_opa_timeout_via_resilience_act_still_fails_closed(monkeypatch):
    """
    S3.5 Chaos scenario: OPA times out (retries exhausted) → resilience returns False.
    Act must escalate, not create approval or execute.
    """
    from apps.common.http_resilience import reset_circuit

    reset_circuit("opa")
    # Simulate OPA client returning False after retries/timeout (patch where act uses it)
    monkeypatch.setattr("apps.agent.nodes.opa_allow", lambda step, inc: False)

    state = _act_state(
        plan=[
            {
                "safe": False,
                "action_type": "restart_service",
                "action": "Restart heater controller",
                "doc_ids": [],
                "snippet_ids": [],
            }
        ],
    )
    result = act(state)

    assert result.get("escalated") is True
    assert (result.get("escalation_packet") or {}).get("reason") == "policy_deny"
    assert (result.get("approval_requests") or []) == []
