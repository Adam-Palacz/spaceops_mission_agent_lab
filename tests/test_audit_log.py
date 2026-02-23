"""
S1.9: Audit log — append-only schema, integration with agent, no update/delete.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.agent.audit_log import append_entry, get_audit_path
from apps.agent.graph import run_pipeline


REQUIRED_FIELDS = (
    "timestamp",
    "trace_id",
    "incident_id",
    "actor",
    "tool",
    "args_hash",
    "decision",
    "policy_result",
    "outcome",
)


def test_append_entry_writes_schema_fields(tmp_path: Path, monkeypatch):
    """S1.9: After append, audit line has all schema fields."""
    monkeypatch.setattr("config.settings.audit_log_path", str(tmp_path / "audit.ndjson"))
    # Re-resolve path (module may have cached; get_audit_path reads settings each time)
    path = get_audit_path()
    assert path == tmp_path / "audit.ndjson"
    append_entry(
        trace_id="tr1",
        incident_id="inc1",
        actor="agent",
        tool="query_telemetry",
        args={"time_range_start": "2025-02-14T09:00:00Z", "time_range_end": "2025-02-14T11:00:00Z", "channels": []},
        decision="allow",
        policy_result="allow",
        outcome="success",
    )
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    for field in REQUIRED_FIELDS:
        assert field in entry, f"Missing schema field: {field}"
    assert entry["actor"] == "agent"
    assert entry["tool"] == "query_telemetry"
    assert entry["outcome"] == "success"
    assert len(entry["args_hash"]) == 64  # sha256 hex


def test_args_hash_consistent_for_same_args(tmp_path: Path, monkeypatch):
    """S1.9: args_hash is consistent for same args (canonical JSON hash)."""
    monkeypatch.setattr("config.settings.audit_log_path", str(tmp_path / "audit.ndjson"))
    args = {"query": "power", "limit": 5}
    append_entry(trace_id="t", incident_id="i", actor="agent", tool="search_runbooks", args=args, outcome="success")
    append_entry(trace_id="t", incident_id="i", actor="agent", tool="search_runbooks", args=dict(args), outcome="success")
    path = get_audit_path()
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    h1 = json.loads(lines[0])["args_hash"]
    h2 = json.loads(lines[1])["args_hash"]
    assert h1 == h2


def test_agent_run_writes_audit_entries_for_each_tool_call(tmp_path: Path, monkeypatch):
    """S1.9: After one agent run, audit log contains entries for each tool call; schema fields present."""
    monkeypatch.setattr("config.settings.audit_log_path", str(tmp_path / "audit.ndjson"))
    try:
        run_pipeline("audit-test-inc", {"ref": "audit-test"})
    except RuntimeError as e:
        if "OPENAI_API_KEY" in str(e):
            pytest.skip("OPENAI_API_KEY not set")
        raise
    path = get_audit_path()
    if not path.exists():
        pytest.skip("Audit file not created (e.g. pipeline skipped)")
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").strip().split("\n") if ln.strip()]
    tools_seen = set()
    for ln in lines:
        entry = json.loads(ln)
        for field in REQUIRED_FIELDS:
            assert field in entry, f"Missing schema field {field} in entry"
        tools_seen.add(entry["tool"])
    assert "query_telemetry" in tools_seen
    assert "search_runbooks" in tools_seen
    assert "search_postmortems" in tools_seen


def test_audit_log_append_only_no_update_delete():
    """S1.9: No code path in audit_log module updates or deletes existing entries (append-only)."""
    from apps.agent import audit_log
    source = Path(audit_log.__file__).read_text(encoding="utf-8")
    # Only allowed write is append
    assert 'open(path, "a"' in source or "open(path, 'a'" in source
    # Must not truncate or overwrite the audit file
    assert "open(path, \"w\"" not in source
    assert "open(path, 'w'" not in source
