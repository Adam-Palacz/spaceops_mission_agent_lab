"""
S2.10 — Act node + OPA: fail-closed behaviour and no execution on deny.

We test that:
- when OPA allows a restricted step, an approval_request is created;
- when OPA denies (or is unavailable → opa_allow returns False), Act escalates and does NOT create an approval_request.
"""

from __future__ import annotations

from typing import Any

from apps.agent.nodes import act


def _make_state(plan: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "incident_id": "inc-opa",
        "trace_id": "trace-opa",
        "plan": plan,
        "act_results": [],
        "approval_requests": [],
    }


def test_act_creates_approval_request_when_opa_allows(monkeypatch):
    """S2.10: safe=False + opa_allow=True → approval_request created, no escalation."""
    created: dict[str, Any] = {}

    def _fake_create(**kwargs: Any) -> str:
        created.update(kwargs)
        return "req-123"

    monkeypatch.setattr("apps.agent.nodes.opa_allow", lambda step, inc: True)
    monkeypatch.setattr("apps.agent.nodes.approval_store_create", _fake_create)

    state = _make_state(
        [
            {
                "safe": False,
                "action_type": "change_config",
                "action": "Increase heater setpoint",
                "doc_ids": ["rb-1"],
                "snippet_ids": [],
            }
        ]
    )
    result = act(state)

    # OPA allowed → one approval_request, not escalated
    approvals = result.get("approval_requests") or []
    assert len(approvals) == 1
    assert approvals[0].get("id") == "req-123"
    assert result.get("escalated") is not True
    # approval_store.create was called with expected fields
    assert created.get("incident_id") == "inc-opa"
    assert created.get("step_index") == 0
    assert created.get("step", {}).get("action_type") == "change_config"


def test_act_escalates_and_does_not_create_request_when_opa_denies(monkeypatch):
    """S2.10: safe=False + opa_allow=False → escalation, no approval_request, no execution."""
    called = {"create": False}

    def _fake_create(**kwargs: Any) -> str:  # pragma: no cover - should not be called
        called["create"] = True
        return "req-should-not-exist"

    monkeypatch.setattr("apps.agent.nodes.opa_allow", lambda step, inc: False)
    monkeypatch.setattr("apps.agent.nodes.approval_store_create", _fake_create)

    state = _make_state(
        [
            {
                "safe": False,
                "action_type": "change_config",
                "action": "Restart all services now",  # would be denied by policy
                "doc_ids": ["rb-2"],
                "snippet_ids": [],
            }
        ]
    )
    result = act(state)

    # OPA denied (or failed) → escalation packet with reason=policy_deny, no approval_requests
    assert result.get("escalated") is True
    packet = result.get("escalation_packet") or {}
    assert packet.get("reason") == "policy_deny"
    approvals = result.get("approval_requests") or []
    assert approvals == []
    # approval_store.create must not be called
    assert called["create"] is False
