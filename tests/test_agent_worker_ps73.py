"""PS7.3 — Variant A graph worker + Postgres run queue tests."""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
from pathlib import Path

import pytest

import config

REPO_ROOT = Path(__file__).resolve().parents[1]
CHART = REPO_ROOT / "deploy" / "helm" / "spaceops"
RUN_QUEUE = REPO_ROOT / "apps" / "agent" / "run_queue.py"
WORKER = REPO_ROOT / "apps" / "workers" / "agent_graph.py"
PS73 = (
    REPO_ROOT
    / "roadmap"
    / "02-production-scale"
    / "sprint-7"
    / "PS7.3-graph-worker-variant-a.md"
)
VARIANT_A_VALUES = CHART / "values-checkpoint-variant-a.yaml"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ps73_deliverables_exist() -> None:
    assert RUN_QUEUE.is_file()
    assert WORKER.is_file()
    assert VARIANT_A_VALUES.is_file()
    assert PS73.is_file()


def test_config_agent_worker_flags() -> None:
    assert hasattr(config.settings, "agent_worker_enabled")
    assert hasattr(config.settings, "agent_run_queue_lease_seconds")


def test_api_enqueue_mode_returns_202(
    api_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config.settings, "agent_worker_enabled", True)
    calls: list[dict] = []

    def fake_enqueue(**kwargs: object) -> object:
        calls.append(kwargs)
        from apps.agent.run_queue import RunQueueJob

        return RunQueueJob(
            run_id=str(kwargs["run_id"]),
            incident_id=str(kwargs["incident_id"]),
            payload=dict(kwargs.get("payload") or {}),
            resume=False,
            replay_source="api",
            status="pending",
        )

    monkeypatch.setattr("apps.agent.run_queue.enqueue_run", fake_enqueue)
    monkeypatch.setattr("apps.agent.run_queue.new_run_id", lambda: "queued-run-1")

    resp = api_client.post(
        "/runs",
        json={"incident_id": "ps73-test", "payload": {"message": "queue me"}},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["run_id"] == "queued-run-1"
    assert calls and calls[0]["incident_id"] == "ps73-test"


def test_worker_process_job_skips_completed_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_module(WORKER, "agent_graph_ps73")
    from apps.agent.run_queue import RunQueueJob

    job = RunQueueJob(
        run_id="done-1",
        incident_id="inc-1",
        payload={},
        resume=False,
        replay_source="api",
        status="processing",
        worker_id="worker-a",
    )
    completed = []

    class FakeCp:
        status = "completed"
        next_node = None

    monkeypatch.setattr(mod, "load_checkpoint", lambda _rid: FakeCp())
    monkeypatch.setattr(
        mod,
        "complete_job",
        lambda rid, *, worker_id: completed.append((rid, worker_id)) or True,
    )
    monkeypatch.setattr(
        mod,
        "run_pipeline",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    mod.process_job(job)
    assert completed == [("done-1", "worker-a")]


def test_worker_process_job_resumes_in_progress_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_module(WORKER, "agent_graph_ps73_resume")
    from apps.agent.run_queue import RunQueueJob

    job = RunQueueJob(
        run_id="mid-1",
        incident_id="inc-2",
        payload={"k": 1},
        resume=False,
        replay_source="api",
        status="processing",
        worker_id="worker-b",
    )
    seen: dict[str, object] = {}

    class FakeCp:
        status = "in_progress"
        next_node = "decide"

    monkeypatch.setattr(mod, "load_checkpoint", lambda _rid: FakeCp())
    monkeypatch.setattr(mod, "complete_job", lambda _rid, *, worker_id: True)

    def fake_pipeline(*_a, **kwargs: object) -> dict:
        seen.update(kwargs)
        return {"run_id": kwargs["run_id"], "escalated": False}

    monkeypatch.setattr(mod, "run_pipeline", fake_pipeline)
    mod.process_job(job)
    assert seen.get("resume") is True
    assert seen.get("run_id") == "mid-1"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set — integration skipped",
)
def test_run_queue_claim_and_complete_roundtrip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import psycopg2

    monkeypatch.setattr(config.settings, "agent_run_queue_lease_seconds", 60)
    from apps.agent.run_queue import (
        claim_next_job,
        complete_job,
        enqueue_run,
        ensure_run_queue_table,
        get_queue_job,
        new_run_id,
    )

    try:
        ensure_run_queue_table()
    except psycopg2.OperationalError:
        pytest.skip("Postgres not reachable at DATABASE_URL")
    run_id = new_run_id()
    enqueue_run(
        run_id=run_id,
        incident_id="ps73-db",
        payload={"n": 1},
        resume=False,
    )
    job = claim_next_job(worker_id="test-worker")
    assert job is not None
    assert job.run_id == run_id
    assert job.worker_id == "test-worker"
    assert complete_job(run_id, worker_id="stale-worker") is False
    still_claimed = get_queue_job(run_id)
    assert still_claimed is not None
    assert still_claimed.status == "processing"
    assert complete_job(run_id, worker_id="test-worker") is True
    final = get_queue_job(run_id)
    assert final is not None
    assert final.status == "done"


def test_helm_variant_a_renders_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    if shutil.which("helm") is None:
        pytest.skip("helm CLI not installed")
    proc = subprocess.run(
        [
            "helm",
            "template",
            "spaceops-va",
            str(CHART),
            "-f",
            str(CHART / "values.yaml"),
            "-f",
            str(CHART / "values-dev.yaml"),
            "-f",
            str(CHART / "values-minimal-dev.yaml"),
            "-f",
            str(VARIANT_A_VALUES),
            "--set",
            "secrets.postgresPassword=test",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "agent-worker" in out
    assert "apps.workers.agent_graph" in out
    assert "AGENT_WORKER_ENABLED" in out
    assert 'value: "true"' in out or "value: true" in out

    def deployment(name: str) -> str:
        match = re.search(
            rf"kind: Deployment\s+metadata:\s+name: {re.escape(name)}\b.*?(?=\n---|\Z)",
            out,
            flags=re.DOTALL,
        )
        assert match, f"Deployment {name} not rendered"
        return match.group(0)

    worker = deployment("spaceops-va-agent-worker")
    api = deployment("spaceops-va-api")
    assert worker.count("- name: AGENT_DURABLE_CHECKPOINT_ENABLED") == 1
    assert api.count("- name: AGENT_DURABLE_CHECKPOINT_ENABLED") == 1
    assert "- name: AGENT_WORKER_ENABLED" not in worker
