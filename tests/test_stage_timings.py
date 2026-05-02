"""PS2.3: _wrap_node records per-node wall time in stage_timings."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from apps.agent.graph import _wrap_node
from apps.agent.state import AgentState


class _FakeSpanCtx:
    def __enter__(self):
        return MagicMock()

    def __exit__(self, *args):
        return False


class _FakeTracer:
    def start_as_current_span(self, _name: str):
        return _FakeSpanCtx()


@pytest.fixture
def fake_tracer(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("apps.agent.graph.get_tracer", lambda _n: _FakeTracer())


def test_wrap_node_appends_ok_timing(fake_tracer: None) -> None:
    def node_fn(_state: AgentState) -> dict:
        return {"subsystem": "x"}

    wrapped = _wrap_node("triage", node_fn)
    state: AgentState = {"incident_id": "i1"}
    out = wrapped(state)
    timings = out.get("stage_timings") or []
    assert len(timings) == 1
    assert timings[0]["node"] == "triage"
    assert timings[0]["status"] == "ok"
    assert isinstance(timings[0]["duration_ms"], int)
    assert timings[0]["duration_ms"] >= 0


def test_wrap_node_chains_existing_timings(fake_tracer: None) -> None:
    def node_fn(_state: AgentState) -> dict:
        return {}

    wrapped = _wrap_node("investigate", node_fn)
    state: AgentState = {
        "incident_id": "i1",
        "stage_timings": [
            {"node": "triage", "duration_ms": 1, "status": "ok"},
        ],
    }
    out = wrapped(state)
    timings = out.get("stage_timings") or []
    assert len(timings) == 2
    assert timings[0]["node"] == "triage"
    assert timings[1]["node"] == "investigate"
    assert timings[1]["status"] == "ok"


def test_wrap_node_propagates_exception_from_node_fn(fake_tracer: None) -> None:
    def node_fn(_state: AgentState) -> dict:
        raise ValueError("boom")

    wrapped = _wrap_node("act", node_fn)
    state: AgentState = {"incident_id": "i1"}
    with pytest.raises(ValueError, match="boom"):
        wrapped(state)
