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
