"""
S1.14: Unit tests for API — GET /health, POST /ingest (validation, persistence).
No Docker or live services; use TestClient and tmp_path for persistence.
"""

from __future__ import annotations

import json
from pathlib import Path

# Sample NDJSON for ingest tests (minimal schema: at least one key per line)
_SAMPLE_NDJSON_VALID = b'{"ts":"2025-02-14T10:00:00Z","channel":"power.bus_voltage","value":28.5}\n{"ts":"2025-02-14T10:01:00Z","channel":"thermal.plate_t","value":22.1}\n'
_SAMPLE_NDJSON_VALID_WITH_EVENT_ID = b'{"event_id":"evt-1","ts":"2025-02-14T10:00:00Z","channel":"power.bus_voltage","value":28.5}\n{"event_id":"evt-2","ts":"2025-02-14T10:01:00Z","channel":"thermal.plate_t","value":22.1}\n'
_SAMPLE_NDJSON_INVALID_JSON = b"not json\n"
_SAMPLE_NDJSON_EMPTY_OBJECT = b"{}\n"
_SAMPLE_NDJSON_NOT_OBJECT = b'["array"]\n'


def _agent_report(
    *,
    incident_id: str,
    run_id: str,
    executive_summary: str,
    citation_refs: list[str] | None = None,
) -> dict:
    return {
        "schema_version": "v1",
        "incident_id": incident_id,
        "run_id": run_id,
        "executive_summary": executive_summary,
        "evidence": [],
        "citation_refs": citation_refs or [],
        "proposed_actions": [],
        "rollback": "N/A",
        "trace_link": "",
    }


def test_health_returns_200_and_body(api_client):
    """GET /health returns 200 and expected body."""
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert "service" in data
    assert data.get("service") == "spaceops-api"


def test_metrics_endpoint_exposes_prometheus_text(api_client):
    """S2.9: GET /metrics returns Prometheus text format."""
    response = api_client.get("/metrics")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/plain")
    body = response.text
    assert "agent_runs_total" in body


def test_ingest_accepts_valid_ndjson_and_persists(api_client, tmp_path: Path):
    """POST /ingest with valid NDJSON returns 201 and persists to data/{source}/."""
    response = api_client.post(
        "/ingest?source=telemetry",
        content=_SAMPLE_NDJSON_VALID,
        headers={"Content-Type": "application/x-ndjson"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body.get("status") == "created"
    assert body.get("source") == "telemetry"
    assert body.get("records") == 2
    assert "path" in body
    assert "telemetry" in body["path"]
    assert "ingest_" in body["path"]
    # Persistence: file exists under DATA_DIR (patched to tmp_path/data)
    data_dir = tmp_path / "data" / "telemetry"
    assert data_dir.exists()
    files = list(data_dir.glob("ingest_*.ndjson"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    lines = [ln for ln in content.strip().split("\n") if ln]
    assert len(lines) == 2


def test_ingest_rejects_empty_body(api_client):
    """POST /ingest with empty body returns 400."""
    response = api_client.post(
        "/ingest?source=telemetry",
        content="",
        headers={"Content-Type": "application/x-ndjson"},
    )
    assert response.status_code == 400


def test_ingest_rejects_invalid_json(api_client):
    """POST /ingest with invalid JSON line returns 400."""
    response = api_client.post(
        "/ingest?source=telemetry",
        content=_SAMPLE_NDJSON_INVALID_JSON,
        headers={"Content-Type": "application/x-ndjson"},
    )
    assert response.status_code == 400
    assert "invalid JSON" in response.json().get("detail", "")


def test_ingest_rejects_empty_object(api_client):
    """POST /ingest with empty JSON object returns 400 (minimal schema: at least one key)."""
    response = api_client.post(
        "/ingest?source=telemetry",
        content=_SAMPLE_NDJSON_EMPTY_OBJECT,
        headers={"Content-Type": "application/x-ndjson"},
    )
    assert response.status_code == 400


def test_ingest_rejects_non_object(api_client):
    """POST /ingest with JSON array (non-object) returns 400."""
    response = api_client.post(
        "/ingest?source=telemetry",
        content=_SAMPLE_NDJSON_NOT_OBJECT,
        headers={"Content-Type": "application/x-ndjson"},
    )
    assert response.status_code == 400


def test_ingest_rejects_invalid_source(api_client):
    """POST /ingest with source not in (telemetry, events, ground_logs) returns 400."""
    response = api_client.post(
        "/ingest?source=invalid",
        content=_SAMPLE_NDJSON_VALID,
        headers={"Content-Type": "application/x-ndjson"},
    )
    assert response.status_code == 400
    assert "source must be one of" in response.json().get("detail", "")


def test_ingest_telemetry_is_idempotent_by_event_id(api_client):
    """PS1.2: duplicate telemetry event_id should not create duplicate records."""
    first = api_client.post(
        "/ingest?source=telemetry",
        content=_SAMPLE_NDJSON_VALID_WITH_EVENT_ID,
        headers={"Content-Type": "application/x-ndjson"},
    )
    assert first.status_code == 201
    first_body = first.json()
    assert first_body.get("accepted") == 2
    assert first_body.get("duplicates") == 0

    second = api_client.post(
        "/ingest?source=telemetry",
        content=_SAMPLE_NDJSON_VALID_WITH_EVENT_ID,
        headers={"Content-Type": "application/x-ndjson"},
    )
    assert second.status_code == 201
    second_body = second.json()
    assert second_body.get("accepted") == 0
    assert second_body.get("duplicates") == 2


def test_ingest_telemetry_contract_validation_error(api_client):
    """PS1.2: telemetry payload that cannot satisfy contract should be rejected."""
    invalid_missing_value = b'{"event_id":"evt-x","ts":"2025-02-14T10:00:00Z","channel":"power.bus_voltage"}\n'
    response = api_client.post(
        "/ingest?source=telemetry",
        content=invalid_missing_value,
        headers={"Content-Type": "application/x-ndjson"},
    )
    assert response.status_code == 400
    detail = response.json().get("detail", {})
    assert isinstance(detail, dict)
    assert detail.get("error") == "validation_failed"
    assert detail.get("rejected", 0) >= 1


def test_ingest_events_source_persists(api_client, tmp_path: Path):
    """POST /ingest?source=events persists to data/events/."""
    response = api_client.post(
        "/ingest?source=events",
        content=_SAMPLE_NDJSON_VALID,
        headers={"Content-Type": "application/x-ndjson"},
    )
    assert response.status_code == 201
    assert (tmp_path / "data" / "events").exists()
    assert response.json().get("source") == "events"


def test_runs_get_empty_when_no_runs(api_client):
    """GET /runs returns empty list when no run files exist."""
    response = api_client.get("/runs")
    assert response.status_code == 200
    assert response.json() == {"runs": []}


def test_runs_get_lists_recent_runs(api_client, tmp_path: Path):
    """GET /runs returns recent run metadata for UI list page (P4.5)."""
    runs_dir = tmp_path / "data" / "incidents"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run1 = runs_dir / "run_inc-1_20260101T010101Z.json"
    run2 = runs_dir / "run_inc-2_20260101T010102Z.json"
    run1.write_text(
        json.dumps(
            {
                "incident_id": "inc-1",
                "report": {"summary": "Power anomaly handled"},
            }
        ),
        encoding="utf-8",
    )
    run2.write_text(
        json.dumps(
            {
                "incident_id": "inc-2",
                "error": "Pipeline failed",
            }
        ),
        encoding="utf-8",
    )

    response = api_client.get("/runs?limit=5")
    assert response.status_code == 200
    runs = response.json().get("runs", [])
    assert len(runs) == 2
    incident_ids = {r.get("incident_id") for r in runs}
    assert {"inc-1", "inc-2"} == incident_ids
    by_incident = {r["incident_id"]: r for r in runs}
    assert by_incident["inc-1"]["status"] == "completed"
    assert by_incident["inc-1"]["summary"] == "Power anomaly handled"
    assert by_incident["inc-2"]["status"] == "error"
    assert by_incident["inc-2"]["error"] == "Pipeline failed"


def test_runs_get_single_run(api_client, tmp_path: Path):
    """GET /runs/{run_key} returns persisted JSON (PS2.1)."""
    runs_dir = tmp_path / "data" / "incidents"
    runs_dir.mkdir(parents=True, exist_ok=True)
    key = "run_inc-x_20260101T010103Z"
    body = {
        "run_id": "abc",
        "incident_id": "inc-x",
        "subsystem": "Power",
        "risk": "high",
        "escalated": False,
        "payload": {},
        "report": {"executive_summary": "ok"},
    }
    (runs_dir / f"{key}.json").write_text(
        json.dumps(body),
        encoding="utf-8",
    )
    response = api_client.get(f"/runs/{key}")
    assert response.status_code == 200
    assert response.json().get("incident_id") == "inc-x"
    assert response.json().get("subsystem") == "Power"


def test_runs_get_rejects_invalid_run_key(api_client):
    assert api_client.get("/runs/evil").status_code == 400
    assert api_client.get("/runs/not_a_run").status_code == 400


def test_runs_get_includes_trace_id_and_trace_link_for_ui_ps25(
    api_client, tmp_path: Path
):
    """GET /runs rows include trace_id / trace_link for Jaeger deep links (PS2.5)."""
    runs_dir = tmp_path / "data" / "incidents"
    runs_dir.mkdir(parents=True, exist_ok=True)
    tid = "a" * 32
    tlink = f"http://localhost:16686/trace/{tid}"
    (runs_dir / "run_inc-trace_20260101T010107Z.json").write_text(
        json.dumps(
            {
                "incident_id": "inc-trace",
                "run_id": "runidhex01",
                "trace_id": tid,
                "report": {"summary": "ok", "trace_link": tlink},
            }
        ),
        encoding="utf-8",
    )
    (runs_dir / "run_inc-notrace_20260101T010108Z.json").write_text(
        json.dumps({"incident_id": "inc-notrace", "report": {"summary": "old"}}),
        encoding="utf-8",
    )
    response = api_client.get("/runs?limit=10")
    assert response.status_code == 200
    by_inc = {r["incident_id"]: r for r in response.json().get("runs", [])}
    row_t = by_inc["inc-trace"]
    assert row_t.get("trace_id") == tid
    assert row_t.get("trace_link") == tlink
    row_n = by_inc["inc-notrace"]
    assert row_n.get("trace_id") in (None, "")
    assert row_n.get("trace_link") in (None, "")


def test_runs_get_filter_subsystem(api_client, tmp_path: Path):
    """GET /runs?subsystem= filters list (PS2.1)."""
    runs_dir = tmp_path / "data" / "incidents"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "run_a_20260101T010104Z.json").write_text(
        json.dumps(
            {
                "incident_id": "a",
                "subsystem": "Power",
                "risk": "low",
                "escalated": False,
                "report": {"executive_summary": "x", "citation_refs": ["r"]},
            }
        ),
        encoding="utf-8",
    )
    (runs_dir / "run_b_20260101T010105Z.json").write_text(
        json.dumps(
            {
                "incident_id": "b",
                "subsystem": "Thermal",
                "risk": "low",
                "escalated": False,
                "report": {"executive_summary": "y"},
            }
        ),
        encoding="utf-8",
    )
    response = api_client.get("/runs?subsystem=Power&limit=10")
    assert response.status_code == 200
    runs = response.json().get("runs", [])
    assert len(runs) == 1
    assert runs[0]["incident_id"] == "a"


def test_runs_simulate_fixture_too_large_returns_413(api_client):
    """PS2.7: oversized upload rejected before pipeline."""
    prefix = b'{"incident_id":"x","payload":{}}'
    body = prefix + b"0" * (52 * 1024)
    response = api_client.post(
        "/runs/simulate",
        files={"file": ("huge.json", body, "application/json")},
    )
    assert response.status_code == 413


def test_runs_simulate_rejects_invalid_fixture(api_client):
    response = api_client.post(
        "/runs/simulate",
        files={"file": ("bad.json", b"not json {", "application/json")},
    )
    assert response.status_code == 400


def test_runs_simulate_quick_validation_returns_422(api_client):
    """PS2.7: quick form requires declared_incident_id, scenario_ref, subsystem, risk."""
    response = api_client.post("/runs/simulate/quick", json={})
    assert response.status_code == 422


def test_runs_simulate_quick_success(api_client, monkeypatch, tmp_path: Path):
    """POST /runs/simulate/quick builds payload server-side."""

    def _fake_pipeline(incident_id, payload=None, replay_source="api"):
        assert str(incident_id).startswith("sim-upload-")
        assert replay_source == "fixture_sim"
        assert payload.get("ref") == "fixture"
        assert payload.get("subsystem") == "Power"
        assert payload.get("risk") == "low"
        return {
            "run_id": "quick-sim-1",
            "report": _agent_report(
                incident_id=str(incident_id),
                run_id="quick-sim-1",
                executive_summary="quick ok",
            ),
            "subsystem": "Power",
            "risk": "low",
            "escalated": False,
            "trace_id": "",
            "stage_timings": [],
        }

    monkeypatch.setattr("apps.agent.graph.run_pipeline", _fake_pipeline)
    response = api_client.post(
        "/runs/simulate/quick",
        json={
            "declared_incident_id": "lab-quick",
            "scenario_ref": "fixture",
            "subsystem_hint": "Power",
            "risk_level": "low",
            "time_range_start": "2025-02-14T09:00:00Z",
            "time_range_end": "2025-02-14T11:00:00Z",
            "channels": "power.bus_voltage, thermal.plate_t",
            "message": "bus glitch",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("simulation") is True
    assert body.get("payload", {}).get("channels") == [
        "power.bus_voltage",
        "thermal.plate_t",
    ]
    assert body.get("payload", {}).get("message") == "bus glitch"


def test_runs_simulate_success_sets_simulation_flag(
    api_client, monkeypatch, tmp_path: Path
):
    """PS2.7: simulate uses isolated incident_id and persists simulation=true."""

    def _fake_pipeline(incident_id, payload=None, replay_source="api"):
        assert str(incident_id).startswith("sim-upload-")
        assert replay_source == "fixture_sim"
        assert isinstance(payload, dict)
        return {
            "run_id": "replay-sim-1",
            "report": _agent_report(
                incident_id=str(incident_id),
                run_id="replay-sim-1",
                executive_summary="sim ok",
            ),
            "subsystem": "Power",
            "risk": "low",
            "escalated": False,
            "trace_id": "",
            "stage_timings": [],
        }

    monkeypatch.setattr("apps.agent.graph.run_pipeline", _fake_pipeline)
    fx = json.dumps({"incident_id": "orig-z", "payload": {"ref": "fixture"}})
    response = api_client.post(
        "/runs/simulate",
        files={"file": ("lab.json", fx.encode("utf-8"), "application/json")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("simulation") is True
    assert body.get("source_fixture_incident_id") == "orig-z"
    assert body.get("run_key")
    assert str(body.get("incident_id") or "").startswith("sim-upload-")

    runs_dir = tmp_path / "data" / "incidents"
    written = list(runs_dir.glob("run_sim-upload*.json"))
    assert len(written) == 1
    disk = json.loads(written[0].read_text(encoding="utf-8"))
    assert disk.get("simulation") is True
    assert disk.get("source_fixture_incident_id") == "orig-z"

    listed = api_client.get("/runs?simulation=true&limit=20").json().get("runs", [])
    assert any(r.get("id") == written[0].stem for r in listed)
    assert all(r.get("simulation") for r in listed if r.get("id") == written[0].stem)


def test_replay_run_endpoint_returns_comparison(api_client, monkeypatch):
    monkeypatch.setattr(
        "apps.replay.workflow.replay_by_run_id",
        lambda _run_id: {
            "run_id": "run-a",
            "replay_run_id": "run-b",
            "incident_id": "inc-1",
            "comparison": {"has_diff": False, "diffs": []},
        },
    )
    response = api_client.post("/replays/run-a/run")
    assert response.status_code == 200
    body = response.json()
    assert body.get("run_id") == "run-a"
    assert body.get("comparison", {}).get("has_diff") is False


def test_replay_run_endpoint_not_found(api_client, monkeypatch):
    def _missing(_run_id: str):
        raise FileNotFoundError("missing replay metadata")

    monkeypatch.setattr("apps.replay.workflow.replay_by_run_id", _missing)
    response = api_client.post("/replays/run-missing/run")
    assert response.status_code == 404


def test_replay_run_endpoint_invalid_metadata(api_client, monkeypatch):
    def _invalid(_run_id: str):
        raise ValueError("bad metadata")

    monkeypatch.setattr("apps.replay.workflow.replay_by_run_id", _invalid)
    response = api_client.post("/replays/run-bad/run")
    assert response.status_code == 422


def test_runs_resume_triggers_pipeline_resume_with_same_run_id(api_client, monkeypatch):
    captured: dict[str, object] = {}

    def _fake_run_pipeline(
        incident_id, payload=None, replay_source="api", run_id=None, resume=False
    ):
        captured["incident_id"] = incident_id
        captured["payload"] = payload
        captured["replay_source"] = replay_source
        captured["run_id"] = run_id
        captured["resume"] = resume
        return {
            "run_id": run_id,
            "report": _agent_report(
                incident_id=str(incident_id),
                run_id=str(run_id),
                executive_summary="resumed",
            ),
        }

    monkeypatch.setattr("apps.agent.graph.run_pipeline", _fake_run_pipeline)
    response = api_client.post(
        "/runs/resume",
        json={
            "run_id": "run-resume-api-1",
            "incident_id": "inc-resume-api",
            "payload": {"ref": "fixture"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "resumed"
    assert body.get("run_id") == "run-resume-api-1"
    assert body.get("incident_id") == "inc-resume-api"
    assert body.get("report", {}).get("executive_summary") == "resumed"

    assert captured["incident_id"] == "inc-resume-api"
    assert captured["payload"] == {"ref": "fixture"}
    assert captured["replay_source"] == "resume"
    assert captured["run_id"] == "run-resume-api-1"
    assert captured["resume"] is True


# ---------------------------------------------------------------------------
# S2.5 Approval API
# ---------------------------------------------------------------------------

_API_KEY = "test-approval-key"


def test_approvals_get_requires_auth(api_client, tmp_path: Path, monkeypatch):
    """GET /approvals without API key returns 401."""
    monkeypatch.setattr("config.settings.approval_api_key", _API_KEY)
    monkeypatch.setattr(
        "config.settings.approval_store_path", str(tmp_path / "approvals")
    )
    response = api_client.get("/approvals")
    assert response.status_code == 401


def test_approvals_get_with_auth_returns_list(api_client, tmp_path: Path, monkeypatch):
    """GET /approvals with valid X-API-Key returns 200 and approvals list."""
    monkeypatch.setattr("config.settings.approval_api_key", _API_KEY)
    monkeypatch.setattr(
        "config.settings.approval_store_path", str(tmp_path / "approvals")
    )
    response = api_client.get("/approvals", headers={"X-API-Key": _API_KEY})
    assert response.status_code == 200
    assert "approvals" in response.json()
    assert isinstance(response.json()["approvals"], list)


def test_approvals_post_approve_without_auth_returns_401(
    api_client, tmp_path: Path, monkeypatch
):
    """POST /approvals/:id/approve without API key returns 401."""
    monkeypatch.setattr("config.settings.approval_api_key", _API_KEY)
    monkeypatch.setattr(
        "config.settings.approval_store_path", str(tmp_path / "approvals")
    )
    monkeypatch.setattr(
        "config.settings.audit_log_path", str(tmp_path / "audit.ndjson")
    )
    response = api_client.post("/approvals/some-id/approve")
    assert response.status_code == 401


def test_approvals_post_reject_without_auth_returns_401(
    api_client, tmp_path: Path, monkeypatch
):
    """POST /approvals/:id/reject without API key returns 401."""
    monkeypatch.setattr("config.settings.approval_api_key", _API_KEY)
    monkeypatch.setattr(
        "config.settings.approval_store_path", str(tmp_path / "approvals")
    )
    response = api_client.post("/approvals/some-id/reject")
    assert response.status_code == 401


def test_approvals_approve_reject_flow_and_idempotent(
    api_client, tmp_path: Path, monkeypatch
):
    """Create approval via store; GET pending; approve with auth; execution runs once (S2.6); second approve is 200 and idempotent (no re-execution); audit has entries."""
    monkeypatch.setattr("config.settings.approval_api_key", _API_KEY)
    monkeypatch.setattr(
        "config.settings.approval_store_path", str(tmp_path / "approvals")
    )
    monkeypatch.setattr(
        "config.settings.audit_log_path", str(tmp_path / "audit.ndjson")
    )
    from apps.agent.approval_store import create as create_approval

    # Mock executor so we don't call real GitOps MCP in tests
    def _mock_execute(approval_id: str, rec: dict):
        return {"outcome": "success", "result": {"pr_url": "", "note": "mocked"}}

    monkeypatch.setattr(
        "apps.agent.approval_executor.execute_approved_action",
        _mock_execute,
    )

    approval_id = create_approval(
        incident_id="inc-1",
        step_index=0,
        step={"action": "Change config", "action_type": "change_config"},
        reason="restricted",
    )
    get_resp = api_client.get("/approvals", headers={"X-API-Key": _API_KEY})
    assert get_resp.status_code == 200
    approvals = get_resp.json().get("approvals", [])
    assert len(approvals) >= 1
    assert any(a.get("id") == approval_id for a in approvals)

    approve_resp = api_client.post(
        f"/approvals/{approval_id}/approve",
        headers={"X-API-Key": _API_KEY, "X-Approval-By": "operator-1"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json().get("status") == "approved"
    assert approve_resp.json().get("approval", {}).get("decided_by") == "operator-1"
    # S2.6: first approve triggers execution once; response includes execution
    assert "execution" in approve_resp.json()
    assert approve_resp.json()["execution"].get("outcome") == "success"

    # Idempotent: second approve returns 200, no execution (no re-run)
    approve_second = api_client.post(
        f"/approvals/{approval_id}/approve",
        headers={"X-API-Key": _API_KEY},
    )
    assert approve_second.status_code == 200
    assert approve_second.json().get("status") == "approved"
    assert "execution" not in approve_second.json()

    # Audit log: human approve + execute_restricted (once)
    audit_path = tmp_path / "audit.ndjson"
    assert audit_path.exists()
    lines = [
        ln for ln in audit_path.read_text(encoding="utf-8").strip().split("\n") if ln
    ]
    assert any("approve" in ln and "human" in ln for ln in lines)
    assert sum(1 for ln in lines if "execute_restricted" in ln) == 1


def test_approvals_approve_execution_failure_recorded(
    api_client, tmp_path: Path, monkeypatch
):
    """S2.6: Failed execution (e.g. GitOps error) is recorded in audit; client gets execution outcome."""
    monkeypatch.setattr("config.settings.approval_api_key", _API_KEY)
    monkeypatch.setattr(
        "config.settings.approval_store_path", str(tmp_path / "approvals")
    )
    monkeypatch.setattr(
        "config.settings.audit_log_path", str(tmp_path / "audit.ndjson")
    )

    def _mock_fail(_aid: str, _rec: dict):
        return {"outcome": "failure", "error_message": "GitOps push failed"}

    monkeypatch.setattr(
        "apps.agent.approval_executor.execute_approved_action",
        _mock_fail,
    )

    from apps.agent.approval_store import create as create_approval

    approval_id = create_approval(
        incident_id="inc-fail",
        step_index=0,
        step={"action": "Change config", "action_type": "change_config"},
        reason="restricted",
    )
    approve_resp = api_client.post(
        f"/approvals/{approval_id}/approve",
        headers={"X-API-Key": _API_KEY},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json().get("status") == "approved"
    assert approve_resp.json().get("execution", {}).get("outcome") == "failure"
    assert "GitOps push failed" in (
        approve_resp.json().get("execution", {}).get("error_message") or ""
    )

    lines = [
        ln
        for ln in (tmp_path / "audit.ndjson")
        .read_text(encoding="utf-8")
        .strip()
        .split("\n")
        if ln
    ]
    assert any("execute_restricted" in ln and "failure" in ln for ln in lines)


def test_approvals_audit_entries_s27(api_client, tmp_path: Path, monkeypatch):
    """S2.7: After one approve and one reject, audit log has two human entries with decision/outcome and schema."""
    monkeypatch.setattr("config.settings.approval_api_key", _API_KEY)
    monkeypatch.setattr(
        "config.settings.approval_store_path", str(tmp_path / "approvals")
    )
    monkeypatch.setattr(
        "config.settings.audit_log_path", str(tmp_path / "audit.ndjson")
    )
    monkeypatch.setattr(
        "apps.agent.approval_executor.execute_approved_action",
        lambda _id, _rec: {"outcome": "success", "result": {}},
    )
    from apps.agent.approval_store import create as create_approval

    id_a = create_approval(
        incident_id="inc-a",
        step_index=0,
        step={"action": "Config A", "action_type": "change_config"},
        reason="restricted",
    )
    id_b = create_approval(
        incident_id="inc-b",
        step_index=0,
        step={"action": "Config B", "action_type": "change_config"},
        reason="restricted",
    )
    api_client.post(
        f"/approvals/{id_a}/approve",
        headers={"X-API-Key": _API_KEY, "X-Approval-By": "op1"},
    )
    api_client.post(
        f"/approvals/{id_b}/reject",
        headers={"X-API-Key": _API_KEY, "X-Approval-By": "op2"},
    )
    lines = [
        ln
        for ln in (tmp_path / "audit.ndjson")
        .read_text(encoding="utf-8")
        .strip()
        .split("\n")
        if ln
    ]
    human_entries = [
        ln for ln in lines if '"human"' in ln and ("approve" in ln or "reject" in ln)
    ]
    assert len(human_entries) >= 2
    required_keys = {
        "timestamp",
        "trace_id",
        "incident_id",
        "actor",
        "tool",
        "args_hash",
        "decision",
        "policy_result",
        "outcome",
    }
    for line in human_entries[:2]:
        entry = json.loads(line)
        for key in required_keys:
            assert key in entry, f"missing {key} in audit entry"
        assert entry.get("actor") == "human"
        assert entry.get("outcome") == "success"
    decisions = {json.loads(ln).get("decision") for ln in human_entries[:2]}
    assert "approve" in decisions and "reject" in decisions


def test_approvals_reject_and_404(api_client, tmp_path: Path, monkeypatch):
    """POST /approvals/:id/reject with auth updates status; unknown id returns 404."""
    monkeypatch.setattr("config.settings.approval_api_key", _API_KEY)
    monkeypatch.setattr(
        "config.settings.approval_store_path", str(tmp_path / "approvals")
    )
    monkeypatch.setattr(
        "config.settings.audit_log_path", str(tmp_path / "audit.ndjson")
    )
    from apps.agent.approval_store import create as create_approval

    approval_id = create_approval(
        incident_id="inc-2",
        step_index=1,
        step={"action": "Restart service", "action_type": "restart_service"},
        reason="restricted",
    )
    reject_resp = api_client.post(
        f"/approvals/{approval_id}/reject",
        headers={"X-API-Key": _API_KEY, "X-Approval-By": "operator-2"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json().get("status") == "rejected"

    not_found = api_client.post(
        "/approvals/00000000-0000-0000-0000-000000000000/approve",
        headers={"X-API-Key": _API_KEY},
    )
    assert not_found.status_code == 404


def test_dlq_telemetry_endpoint_returns_rows(api_client, monkeypatch):
    class DummyConn:
        def close(self):
            return None

    monkeypatch.setattr("psycopg2.connect", lambda _dsn: DummyConn())
    monkeypatch.setattr(
        "apps.workers.telemetry_persist.list_dlq_events",
        lambda _conn, limit=100: [
            {
                "event_id": "evt-1",
                "reason": "persist_failure",
                "retry_count": 3,
                "next_retry_at": None,
                "last_error": "boom",
                "last_error_hash": "h",
                "run_id": None,
                "incident_id": None,
                "subject": "ingest.telemetry",
                "payload": {"k": 1},
                "created_at": "2026-05-05T12:00:00+00:00",
            }
        ],
    )
    response = api_client.get("/dlq/telemetry?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["dlq_events"][0]["event_id"] == "evt-1"


def test_dlq_telemetry_endpoint_db_unavailable(api_client, monkeypatch):
    monkeypatch.setattr(
        "psycopg2.connect",
        lambda _dsn: (_ for _ in ()).throw(RuntimeError("db down")),
    )
    response = api_client.get("/dlq/telemetry")
    assert response.status_code == 503
