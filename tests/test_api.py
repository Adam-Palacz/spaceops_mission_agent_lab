"""
S1.14: Unit tests for API — GET /health, POST /ingest (validation, persistence).
No Docker or live services; use TestClient and tmp_path for persistence.
"""

from __future__ import annotations

from pathlib import Path

# Sample NDJSON for ingest tests (minimal schema: at least one key per line)
_SAMPLE_NDJSON_VALID = b'{"ts":"2025-02-14T10:00:00Z","channel":"power.bus_voltage","value":28.5}\n{"ts":"2025-02-14T10:01:00Z","channel":"thermal.plate_t","value":22.1}\n'
_SAMPLE_NDJSON_INVALID_JSON = b"not json\n"
_SAMPLE_NDJSON_EMPTY_OBJECT = b"{}\n"
_SAMPLE_NDJSON_NOT_OBJECT = b'["array"]\n'


def test_health_returns_200_and_body(api_client):
    """GET /health returns 200 and expected body."""
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert "service" in data
    assert data.get("service") == "spaceops-api"


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
    """Create approval via store; GET pending; approve with auth; second approve is 200 and idempotent; audit has entry."""
    monkeypatch.setattr("config.settings.approval_api_key", _API_KEY)
    monkeypatch.setattr(
        "config.settings.approval_store_path", str(tmp_path / "approvals")
    )
    monkeypatch.setattr(
        "config.settings.audit_log_path", str(tmp_path / "audit.ndjson")
    )
    from apps.agent.approval_store import create as create_approval

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

    # Idempotent: second approve returns 200 and does not change outcome
    approve_second = api_client.post(
        f"/approvals/{approval_id}/approve",
        headers={"X-API-Key": _API_KEY},
    )
    assert approve_second.status_code == 200
    assert approve_second.json().get("status") == "approved"

    # Audit log contains human approve entry
    audit_path = tmp_path / "audit.ndjson"
    assert audit_path.exists()
    lines = [
        ln for ln in audit_path.read_text(encoding="utf-8").strip().split("\n") if ln
    ]
    assert any("approve" in ln and "human" in ln for ln in lines)


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
