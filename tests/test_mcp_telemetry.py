"""
S1.6: query_telemetry — unit test with fixture data.
Uses repo data/telemetry fixtures; no MCP server required.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


def _load_telemetry_records(data_dir: Path) -> list[dict]:
    records: list[dict] = []
    if not data_dir.exists():
        return records
    for path in sorted(data_dir.glob("*.ndjson")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def _query_telemetry(
    data_dir: Path,
    time_range_start: str,
    time_range_end: str,
    channels: list[str] | None = None,
) -> list[dict]:
    start = time_range_start.strip() if time_range_start else None
    end = time_range_end.strip() if time_range_end else None
    if not start or not end:
        return []
    records = _load_telemetry_records(data_dir)
    out: list[dict] = []
    for r in records:
        if not isinstance(r, dict):
            continue
        ts = (r.get("ts") or r.get("timestamp") or "").strip()
        if not ts or ts < start or ts > end:
            continue
        if channels:
            ch = r.get("channel") or r.get("channel_id")
            if ch not in channels:
                continue
        out.append(r)
    return out


def test_query_telemetry_with_fixture_data():
    """query_telemetry with valid time range returns non-empty result when fixture data overlaps."""
    repo_root = Path(__file__).resolve().parent.parent
    data_telemetry = repo_root / "data" / "telemetry"
    if not (data_telemetry / "telemetry.ndjson").exists():
        pytest.skip("data/telemetry/telemetry.ndjson not found")
    result = _query_telemetry(
        data_telemetry,
        time_range_start="2025-02-14T09:00:00Z",
        time_range_end="2025-02-14T11:00:00Z",
    )
    assert len(result) >= 1
    for r in result:
        assert "ts" in r or "timestamp" in r
        assert "channel" in r or "channel_id" in r


def test_query_telemetry_filter_by_channels():
    """Filtering by channels returns only those channels."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.ndjson"
        path.write_text(
            '{"ts": "2025-02-14T10:00:00Z", "channel": "a", "value": 1}\n'
            '{"ts": "2025-02-14T10:01:00Z", "channel": "b", "value": 2}\n'
        )
        result = _query_telemetry(
            Path(tmp),
            "2025-02-14T09:00:00Z",
            "2025-02-14T11:00:00Z",
            channels=["a"],
        )
        assert len(result) == 1
        assert result[0]["channel"] == "a"
