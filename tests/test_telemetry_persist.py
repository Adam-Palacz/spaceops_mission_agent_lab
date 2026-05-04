"""Unit tests for Postgres telemetry insert helpers (PS3.2)."""

from __future__ import annotations

from datetime import timezone

from apps.workers.telemetry_persist import coerce_value_to_float, parse_ts_iso


def test_parse_ts_iso_z_suffix():
    dt = parse_ts_iso("2025-02-14T10:00:00Z")
    assert dt.tzinfo == timezone.utc


def test_coerce_value_to_float():
    assert coerce_value_to_float(28.5) == 28.5
    assert coerce_value_to_float(3) == 3.0
    assert coerce_value_to_float("1.25") == 1.25
    assert coerce_value_to_float("nanana") == 0.0
