"""
S1.14 — Shared pytest fixtures: sample NDJSON, API client with isolated data dir.
Tests do not require Docker or live Postgres/LLM (mocks or tmp paths).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Must run before `import config` so Settings reads isolated paths and no OTLP export.
_test_tmp = tempfile.mkdtemp(prefix="pytest_session_")
os.environ["AUDIT_LOG_PATH"] = os.path.join(_test_tmp, "audit.ndjson")
os.environ["APPROVAL_STORE_PATH"] = os.path.join(_test_tmp, "approvals")
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = ""

import config  # noqa: E402

# Sample valid NDJSON lines for ingest tests (minimal schema: at least one key per line)
SAMPLE_NDJSON_VALID = b'{"ts":"2025-02-14T10:00:00Z","channel":"power.bus_voltage","value":28.5}\n{"ts":"2025-02-14T10:01:00Z","channel":"thermal.plate_t","value":22.1}\n'
SAMPLE_NDJSON_VALID_WITH_EVENT_ID = b'{"event_id":"evt-1","ts":"2025-02-14T10:00:00Z","channel":"power.bus_voltage","value":28.5}\n{"event_id":"evt-2","ts":"2025-02-14T10:01:00Z","channel":"thermal.plate_t","value":22.1}\n'
SAMPLE_NDJSON_INVALID_JSON = b"not json\n"
SAMPLE_NDJSON_EMPTY_OBJECT = b"{}\n"
SAMPLE_NDJSON_NOT_OBJECT = b'["array"]\n'


@pytest.fixture(autouse=True)
def _default_test_settings(monkeypatch):
    """
    Keep test behavior deterministic regardless of local .env overrides.

    PS3.9 durable checkpoints are feature-flagged and should be opt-in per test;
    otherwise baseline tests that assert legacy run_pipeline flow may become flaky.
    """
    monkeypatch.setattr(config.settings, "audit_log_path", os.environ["AUDIT_LOG_PATH"])
    monkeypatch.setattr(
        config.settings, "approval_store_path", os.environ["APPROVAL_STORE_PATH"]
    )
    monkeypatch.setattr(config.settings, "otel_exporter_otlp_endpoint", "")
    monkeypatch.setattr(config.settings, "agent_durable_checkpoint_enabled", False)
    yield


@pytest.fixture
def api_client(tmp_path: Path, monkeypatch):
    """
    FastAPI TestClient for the API app; DATA_DIR and REPO_ROOT patched to tmp_path so ingest persists under tmp_path
    and path.relative_to(REPO_ROOT) in the response succeeds.
    """
    monkeypatch.setattr("apps.api.main.REPO_ROOT", tmp_path)
    monkeypatch.setattr("apps.api.main.DATA_DIR", tmp_path / "data")
    # .env may set NATS_URL; without a broker ingest would return 503. Default tests = file ingest (201).
    monkeypatch.setattr(config.settings, "nats_url", "")
    from fastapi.testclient import TestClient
    from apps.api.main import app

    with TestClient(app) as client:
        yield client
