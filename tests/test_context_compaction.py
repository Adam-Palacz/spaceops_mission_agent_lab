"""
S3.3 — Context window & memory compaction.

Ensure that compact_history() bounds hypotheses and citations length based on config,
without affecting small/normal states.
"""

from __future__ import annotations

from apps.agent.state import AgentState, compact_history


def test_compact_history_trims_large_state(monkeypatch):
    # Configure small limits to force compaction.
    monkeypatch.setattr("config.settings.agent_max_hypotheses", 3, raising=False)
    monkeypatch.setattr("config.settings.agent_max_citations", 5, raising=False)

    state: AgentState = {
        "incident_id": "comp-1",
        "hypotheses": [f"h{i}" for i in range(10)],
        "citations": [
            {"doc_id": f"d{i}", "snippet_id": f"s{i}", "content": "..."}
            for i in range(10)
        ],
    }

    delta = compact_history(state)
    assert "hypotheses" in delta
    assert "citations" in delta
    assert len(delta["hypotheses"]) == 3
    assert len(delta["citations"]) == 5


def test_compact_history_noop_for_small_state(monkeypatch):
    monkeypatch.setattr("config.settings.agent_max_hypotheses", 10, raising=False)
    monkeypatch.setattr("config.settings.agent_max_citations", 10, raising=False)

    state: AgentState = {
        "incident_id": "comp-2",
        "hypotheses": ["h1", "h2"],
        "citations": [{"doc_id": "d1", "snippet_id": "s1", "content": "..."}],
    }

    delta = compact_history(state)
    assert delta == {}
