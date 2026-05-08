from __future__ import annotations

from typing import Any

import pytest

from apps.agent import graph as graph_mod
from apps.agent.checkpointing import CheckpointRecord
from apps.agent.state import AgentState


def test_interrupt_then_resume_keeps_state_continuity(monkeypatch: pytest.MonkeyPatch):
    store: dict[str, dict[str, Any]] = {}

    def fake_upsert_checkpoint(
        *,
        run_id: str,
        thread_id: str,
        incident_id: str,
        status: str,
        next_node: str | None,
        state: dict[str, Any],
    ) -> None:
        store[run_id] = {
            "run_id": run_id,
            "thread_id": thread_id,
            "incident_id": incident_id,
            "status": status,
            "next_node": next_node,
            "state": dict(state),
            "updated_at": "now",
        }

    def fake_load_checkpoint(run_id: str) -> CheckpointRecord | None:
        row = store.get(run_id)
        if not row:
            return None
        return CheckpointRecord(
            run_id=str(row["run_id"]),
            thread_id=str(row["thread_id"]),
            incident_id=str(row["incident_id"]),
            status=str(row["status"]),
            next_node=row["next_node"],
            state=dict(row["state"]),
            updated_at=str(row["updated_at"]),
        )

    calls = {"investigate": 0}

    def triage(state: AgentState) -> dict[str, Any]:
        return {"subsystem": "Power", "triaged_marker": "t1"}

    def investigate(state: AgentState) -> dict[str, Any]:
        calls["investigate"] += 1
        if calls["investigate"] == 1:
            raise RuntimeError("simulated restart during investigate")
        return {"hypotheses": ["ok"], "citations": [{"doc_id": "r1"}]}

    def check_escalation(state: AgentState) -> dict[str, Any]:
        return {"escalated": False, "escalation_packet": {}}

    def decide(state: AgentState) -> dict[str, Any]:
        return {"plan": [{"action": "noop", "action_type": "report"}]}

    def act(state: AgentState) -> dict[str, Any]:
        return {"act_results": [{"status": "noop"}]}

    def report(state: AgentState) -> dict[str, Any]:
        return {"report": {"incident_id": state.get("incident_id", ""), "ok": True}}

    monkeypatch.setattr(graph_mod, "upsert_checkpoint", fake_upsert_checkpoint)
    monkeypatch.setattr(graph_mod, "load_checkpoint", fake_load_checkpoint)
    monkeypatch.setattr(graph_mod, "triage", triage)
    monkeypatch.setattr(graph_mod, "investigate", investigate)
    monkeypatch.setattr(graph_mod, "check_escalation", check_escalation)
    monkeypatch.setattr(graph_mod, "decide", decide)
    monkeypatch.setattr(graph_mod, "act", act)
    monkeypatch.setattr(graph_mod, "report_node_fn", report)

    run_id = "run-resume-1"
    initial: AgentState = {
        "run_id": run_id,
        "incident_id": "inc-resume",
        "trace_id": "trace-x",
        "payload": {"ref": "fixture"},
    }

    with pytest.raises(RuntimeError, match="simulated restart"):
        graph_mod._run_with_durable_checkpoint(
            run_id=run_id,
            incident_id="inc-resume",
            initial=initial,
            resume=False,
        )

    cp = store[run_id]
    assert cp["status"] == "in_progress"
    assert cp["next_node"] == "investigate"
    assert cp["state"].get("triaged_marker") == "t1"

    final = graph_mod._run_with_durable_checkpoint(
        run_id=run_id,
        incident_id="inc-resume",
        initial=initial,
        resume=True,
    )
    assert final.get("triaged_marker") == "t1"
    assert final.get("report", {}).get("ok") is True
    assert store[run_id]["status"] == "completed"
    assert store[run_id]["next_node"] is None
