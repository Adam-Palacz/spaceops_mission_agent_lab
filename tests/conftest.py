"""
S1.14 — Shared pytest fixtures: sample NDJSON, API client with isolated data dir.
Tests do not require Docker or live Postgres/LLM (mocks or tmp paths).
"""
from __future__ import annotations

from pathlib import Path

import pytest


# Sample valid NDJSON lines for ingest tests (minimal schema: at least one key per line)
SAMPLE_NDJSON_VALID = b'{"ts":"2025-02-14T10:00:00Z","channel":"power.bus_voltage","value":28.5}\n{"ts":"2025-02-14T10:01:00Z","channel":"thermal.plate_t","value":22.1}\n'
SAMPLE_NDJSON_INVALID_JSON = b"not json\n"
SAMPLE_NDJSON_EMPTY_OBJECT = b"{}\n"
SAMPLE_NDJSON_NOT_OBJECT = b'["array"]\n'


@pytest.fixture
def api_client(tmp_path: Path, monkeypatch):
    """
    FastAPI TestClient for the API app; DATA_DIR and REPO_ROOT patched to tmp_path so ingest persists under tmp_path
    and path.relative_to(REPO_ROOT) in the response succeeds.
    """
    monkeypatch.setattr("apps.api.main.REPO_ROOT", tmp_path)
    monkeypatch.setattr("apps.api.main.DATA_DIR", tmp_path / "data")
    from fastapi.testclient import TestClient
    from apps.api.main import app
    return TestClient(app)
