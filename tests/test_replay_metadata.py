from __future__ import annotations

import json
from pathlib import Path

from apps.agent.graph import run_pipeline
from apps.replay.metadata import load_replay_metadata


class _FakeGraph:
    def __init__(self, response: dict):
        self._response = response

    def invoke(self, _initial: dict) -> dict:
        return dict(self._response)


def test_run_pipeline_persists_replay_metadata(monkeypatch, tmp_path: Path):
    replay_dir = tmp_path / "data" / "replay" / "runs"
    monkeypatch.setattr("apps.replay.metadata.REPLAY_RUNS_DIR", replay_dir)
    monkeypatch.setattr("apps.agent.graph.init_telemetry", lambda *args, **kwargs: None)

    class _Span:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def set_attribute(self, *_args, **_kwargs):
            return None

    class _Tracer:
        def start_as_current_span(self, _name: str):
            return _Span()

    monkeypatch.setattr(
        "apps.agent.graph.get_tracer", lambda *_args, **_kwargs: _Tracer()
    )
    monkeypatch.setattr("apps.agent.graph.get_current_trace_id_hex", lambda: "a" * 32)
    monkeypatch.setattr(
        "apps.agent.graph.build_graph",
        lambda: _FakeGraph(
            {
                "trace_id": "a" * 32,
                "llm_calls_used": 2,
                "plan": [{"action": "noop", "action_type": "report"}],
            }
        ),
    )

    result = run_pipeline(
        "inc-replay-1",
        {"event_ids": ["evt-1", "evt-2"], "message": "test"},
        replay_source="eval_standard",
    )
    run_id = result.get("run_id")
    assert isinstance(run_id, str) and run_id
    metadata = load_replay_metadata(run_id)
    assert metadata["schema_version"] == "v1"
    assert metadata["incident_id"] == "inc-replay-1"
    assert metadata["replay_source"] == "eval_standard"
    assert metadata["trace_id"] == "a" * 32
    assert metadata["input_refs"] == ["evt-1", "evt-2"]
    assert metadata["llm_calls_used"] == 2
    assert metadata["payload_hash"]
    assert metadata["prompts"]["triage"] == "v1"
    assert metadata["prompts"]["decide"] == "v1"


def test_get_replay_metadata_endpoint_success(api_client, monkeypatch, tmp_path: Path):
    replay_dir = tmp_path / "data" / "replay" / "runs"
    monkeypatch.setattr("apps.replay.metadata.REPLAY_RUNS_DIR", replay_dir)
    replay_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "v1",
        "run_id": "run-ok",
        "incident_id": "inc-1",
        "payload_hash": "abc",
        "trace_id": "trace-1",
        "model": {"provider": "openai", "model_id": "gpt-4o-mini"},
        "prompts": {"triage": "v1", "decide": "v1"},
        "runtime": {"python_version": "3.12.0", "platform": "test"},
    }
    (replay_dir / "run-ok.json").write_text(json.dumps(payload), encoding="utf-8")

    response = api_client.get("/replays/run-ok")
    assert response.status_code == 200
    replay = response.json().get("replay", {})
    assert replay.get("run_id") == "run-ok"
    assert replay.get("incident_id") == "inc-1"


def test_get_replay_metadata_endpoint_missing_returns_404(api_client):
    response = api_client.get("/replays/missing-run")
    assert response.status_code == 404
    assert "Replay metadata not found" in (response.json().get("detail") or "")


def test_get_replay_metadata_endpoint_incomplete_returns_422(
    api_client, monkeypatch, tmp_path: Path
):
    replay_dir = tmp_path / "data" / "replay" / "runs"
    monkeypatch.setattr("apps.replay.metadata.REPLAY_RUNS_DIR", replay_dir)
    replay_dir.mkdir(parents=True, exist_ok=True)
    (replay_dir / "bad-run.json").write_text(
        json.dumps({"schema_version": "v1", "run_id": "bad-run"}),
        encoding="utf-8",
    )

    response = api_client.get("/replays/bad-run")
    assert response.status_code == 422
    assert "incomplete" in (response.json().get("detail") or "")
