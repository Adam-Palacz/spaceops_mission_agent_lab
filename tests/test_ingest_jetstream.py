"""PS3.2 — JetStream ingest path (mocked NATS)."""

from __future__ import annotations

from tests.conftest import SAMPLE_NDJSON_VALID_WITH_EVENT_ID


def test_ingest_telemetry_jetstream_returns_202(monkeypatch, tmp_path):
    monkeypatch.setattr("apps.api.main.REPO_ROOT", tmp_path)
    monkeypatch.setattr("apps.api.main.DATA_DIR", tmp_path / "data")
    monkeypatch.setattr("config.settings.nats_url", "nats://mock:4222")

    captured: list[list] = []

    async def fake_get_js(app):
        return object()

    async def fake_publish(js, records):
        captured.append(records)
        return (len(records), 0, 0)

    monkeypatch.setattr(
        "apps.ingest_jetstream.get_or_create_js",
        fake_get_js,
    )
    monkeypatch.setattr(
        "apps.ingest_jetstream.publish_telemetry_records",
        fake_publish,
    )

    from fastapi.testclient import TestClient
    from apps.api.main import app

    with TestClient(app) as client:
        response = client.post(
            "/ingest?source=telemetry",
            content=SAMPLE_NDJSON_VALID_WITH_EVENT_ID,
            headers={"Content-Type": "application/x-ndjson"},
        )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["ingest_mode"] == "jetstream"
    assert body["records"] == 2
    assert body["accepted"] == 2
    assert len(captured) == 1
    assert len(captured[0]) == 2


def test_ingest_jetstream_duplicate_counts(monkeypatch, tmp_path):
    monkeypatch.setattr("apps.api.main.REPO_ROOT", tmp_path)
    monkeypatch.setattr("apps.api.main.DATA_DIR", tmp_path / "data")
    monkeypatch.setattr("config.settings.nats_url", "nats://mock:4222")

    async def fake_get_js(app):
        return object()

    async def fake_publish(js, records):
        return (1, 1, 2)

    monkeypatch.setattr("apps.ingest_jetstream.get_or_create_js", fake_get_js)
    monkeypatch.setattr(
        "apps.ingest_jetstream.publish_telemetry_records",
        fake_publish,
    )

    from fastapi.testclient import TestClient
    from apps.api.main import app

    with TestClient(app) as client:
        response = client.post(
            "/ingest?source=telemetry",
            content=SAMPLE_NDJSON_VALID_WITH_EVENT_ID,
            headers={"Content-Type": "application/x-ndjson"},
        )

    assert response.status_code == 202
    assert response.json()["accepted"] == 1
    assert response.json()["duplicates"] == 3
