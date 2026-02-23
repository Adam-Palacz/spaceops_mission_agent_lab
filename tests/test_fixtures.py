"""
S1.14: Unit tests for fixture loading / schema — NDJSON under data/ (same rules as ingest).
Deterministic; no Docker or live services.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


def _ndjson_lines(path: Path) -> list[dict]:
    """Load NDJSON file; return list of dicts. Raises if any line is invalid or empty object."""
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").strip().split("\n"), start=1):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError(f"Line {i}: expected JSON object, got {type(obj)}")
        if not obj:
            raise ValueError(f"Line {i}: empty object")
        out.append(obj)
    return out


def test_telemetry_fixture_schema_if_present():
    """If data/telemetry/telemetry.ndjson exists, each line is valid JSON object with at least one key."""
    path = DATA_DIR / "telemetry" / "telemetry.ndjson"
    if not path.exists():
        return  # skip when fixture not present
    records = _ndjson_lines(path)
    assert len(records) >= 1
    for rec in records:
        assert isinstance(rec, dict)
        assert len(rec) >= 1


def test_events_fixture_schema_if_present():
    """If data/events/events.ndjson exists, each line is valid JSON object."""
    path = DATA_DIR / "events" / "events.ndjson"
    if not path.exists():
        return
    records = _ndjson_lines(path)
    assert len(records) >= 1
    for rec in records:
        assert isinstance(rec, dict)
        assert len(rec) >= 1
