from __future__ import annotations

import json
from pathlib import Path

from apps.replay.workflow import replay_by_run_id


def test_replay_workflow_no_diff(monkeypatch, tmp_path: Path):
    replay_dir = tmp_path / "data" / "replay" / "runs"
    run_dir = tmp_path / "data" / "incidents"
    replay_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("apps.replay.metadata.REPLAY_RUNS_DIR", replay_dir)
    monkeypatch.setattr("apps.replay.workflow.RUN_ARTIFACTS_DIR", run_dir)
    (replay_dir / "r-1.json").write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "run_id": "r-1",
                "incident_id": "inc-1",
                "payload_hash": "abc",
                "trace_id": "trace-1",
                "replay_source": "api",
                "model": {"provider": "openai", "model_id": "m"},
                "prompts": {"triage": "v1", "decide": "v1"},
                "runtime": {"python_version": "3.12", "platform": "test"},
                "original_outcome": {
                    "subsystem": "Power",
                    "escalated": False,
                    "has_citations": True,
                },
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "run_inc-1_x.json").write_text(
        json.dumps(
            {"run_id": "r-1", "incident_id": "inc-1", "payload": {"message": "x"}}
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "apps.replay.workflow.run_pipeline",
        lambda **_kwargs: {
            "run_id": "replay-1",
            "subsystem": "Power",
            "escalated": False,
            "citations": [{"doc_id": "rb"}],
            "report": {"citation_refs": ["rb"]},
        },
    )
    out = replay_by_run_id("r-1")
    assert out["comparison"]["has_diff"] is False
    assert out["comparison"]["diffs"] == []


def test_replay_workflow_detects_diff(monkeypatch, tmp_path: Path):
    replay_dir = tmp_path / "data" / "replay" / "runs"
    run_dir = tmp_path / "data" / "incidents"
    replay_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("apps.replay.metadata.REPLAY_RUNS_DIR", replay_dir)
    monkeypatch.setattr("apps.replay.workflow.RUN_ARTIFACTS_DIR", run_dir)
    (replay_dir / "r-2.json").write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "run_id": "r-2",
                "incident_id": "inc-2",
                "payload_hash": "abc",
                "trace_id": "trace-2",
                "replay_source": "api",
                "model": {"provider": "openai", "model_id": "m"},
                "prompts": {"triage": "v1", "decide": "v1"},
                "runtime": {"python_version": "3.12", "platform": "test"},
                "original_outcome": {
                    "subsystem": "Power",
                    "escalated": False,
                    "has_citations": True,
                },
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "run_inc-2_x.json").write_text(
        json.dumps(
            {"run_id": "r-2", "incident_id": "inc-2", "payload": {"message": "x"}}
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "apps.replay.workflow.run_pipeline",
        lambda **_kwargs: {
            "run_id": "replay-2",
            "subsystem": "Thermal",
            "escalated": True,
            "citations": [],
            "report": {"citation_refs": []},
        },
    )
    out = replay_by_run_id("r-2")
    assert out["comparison"]["has_diff"] is True
    fields = {d["field"] for d in out["comparison"]["diffs"]}
    assert {"subsystem", "escalated", "has_citations"} <= fields
