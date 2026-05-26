"""
PS4.6 — Behavior metrics: normalization, emission on completed and escalated runs.
"""

from __future__ import annotations

import re

from prometheus_client import REGISTRY, generate_latest

from apps.behavior_metrics import (
    normalize_escalation_reason,
    normalize_evidence_policy_status,
    normalize_stage,
    record_agent_run_behavior,
    record_agent_run_error,
)


def _metric_samples(body: str, metric: str) -> list[tuple[dict[str, str], float]]:
    """Parse Prometheus text exposition for a single metric family."""
    out: list[tuple[dict[str, str], float]] = []
    for line in body.splitlines():
        if not line.startswith(metric) or line.startswith(f"{metric}_"):
            continue
        if line.startswith("#"):
            continue
        m = re.match(
            rf"^{re.escape(metric)}\{{([^}}]*)\}}\s+([0-9.eE+-]+)$",
            line,
        )
        if not m:
            m = re.match(rf"^{re.escape(metric)}\s+([0-9.eE+-]+)$", line)
            if m:
                out.append(({}, float(m.group(1))))
            continue
        labels: dict[str, str] = {}
        for part in m.group(1).split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                labels[k] = v.strip('"')
        out.append((labels, float(m.group(2))))
    return out


def _sum_labels(body: str, metric: str, **want: str) -> float:
    total = 0.0
    for labels, value in _metric_samples(body, metric):
        if all(labels.get(k) == v for k, v in want.items()):
            total += value
    return total


def test_normalize_escalation_reason_maps_unknown_to_other():
    assert normalize_escalation_reason("no_evidence") == "no_evidence"
    assert normalize_escalation_reason("CUSTOM") == "other"


def test_normalize_stage_and_evidence_policy():
    assert normalize_stage("triage") == "triage"
    assert normalize_stage("unknown-node") == "other"
    assert normalize_evidence_policy_status("ok") == "ok"
    assert normalize_evidence_policy_status("") == "unknown"


def test_record_completed_run_emits_behavior_metrics():
    before = generate_latest(REGISTRY).decode()
    b_completed_before = _sum_labels(
        before, "agent_behavior_runs_total", outcome="completed"
    )

    record_agent_run_behavior(
        {
            "escalated": False,
            "evidence_policy_status": "ok",
            "citations": [{"doc_id": "rb-1"}],
            "stage_timings": [
                {"node": "triage", "duration_ms": 120, "status": "ok"},
                {"node": "investigate", "duration_ms": 450, "status": "ok"},
            ],
        },
        2.0,
    )

    after = generate_latest(REGISTRY).decode()
    assert (
        _sum_labels(after, "agent_behavior_runs_total", outcome="completed")
        == b_completed_before + 1
    )
    assert (
        _sum_labels(
            after,
            "agent_evidence_coverage_total",
            policy_status="ok",
            has_citations="true",
        )
        >= 1
    )
    assert "agent_stage_duration_seconds_bucket" in after
    assert 'stage="triage"' in after


def test_record_emits_tool_outcome_metrics():
    before = generate_latest(REGISTRY).decode()
    b_before = _sum_labels(
        before, "agent_tool_outcome_total", tool="create_ticket", outcome="failure"
    )

    record_agent_run_behavior(
        {
            "escalated": False,
            "evidence_policy_status": "ok",
            "citations": [],
            "tool_outcomes": {"query_telemetry": "failure", "search_runbooks": "empty"},
            "act_results": [
                {"tool": "create_ticket", "outcome": "failure"},
                {"tool": "create_pr", "outcome": "success"},
            ],
            "stage_timings": [],
        },
        1.0,
    )

    after = generate_latest(REGISTRY).decode()
    assert (
        _sum_labels(
            after, "agent_tool_outcome_total", tool="create_ticket", outcome="failure"
        )
        == b_before + 1
    )
    assert (
        _sum_labels(
            after, "agent_tool_outcome_total", tool="query_telemetry", outcome="failure"
        )
        >= 1
    )


def test_record_escalated_run_increments_escalation_counter():
    before = generate_latest(REGISTRY).decode()
    b_esc_before = _sum_labels(
        before, "agent_escalations_total", reason="prompt_injection_detected"
    )

    record_agent_run_behavior(
        {
            "escalated": True,
            "escalation_packet": {"reason": "prompt_injection_detected"},
            "evidence_policy_status": "skipped_escalated",
            "citations": [],
            "stage_timings": [{"node": "act", "duration_ms": 10, "status": "ok"}],
        },
        0.5,
    )

    after = generate_latest(REGISTRY).decode()
    assert _sum_labels(after, "agent_behavior_runs_total", outcome="escalated") >= 1
    assert (
        _sum_labels(
            after, "agent_escalations_total", reason="prompt_injection_detected"
        )
        == b_esc_before + 1
    )


def test_record_error_increments_error_outcome():
    before = generate_latest(REGISTRY).decode()
    b_err_before = _sum_labels(before, "agent_behavior_runs_total", outcome="error")
    record_agent_run_error(1.0)
    after = generate_latest(REGISTRY).decode()
    assert (
        _sum_labels(after, "agent_behavior_runs_total", outcome="error")
        == b_err_before + 1
    )


def _agent_report(incident_id: str, run_id: str) -> dict:
    return {
        "schema_version": "v1",
        "incident_id": incident_id,
        "run_id": run_id,
        "executive_summary": "test",
        "evidence": [],
        "citation_refs": [],
        "proposed_actions": [],
        "rollback": "N/A",
        "trace_link": "",
    }


def test_api_run_emits_ps46_metrics_on_escalation(api_client, monkeypatch):
    """POST /runs records behavior metrics exposed on GET /metrics."""

    def _fake_pipeline(incident_id: str, payload: dict, **kwargs: object) -> dict:
        return {
            "run_id": "run-ps46",
            "trace_id": "trace-ps46",
            "escalated": True,
            "escalation_packet": {"reason": "no_evidence"},
            "evidence_policy_status": "skipped_escalated",
            "citations": [],
            "stage_timings": [
                {"node": "check_escalation", "duration_ms": 5, "status": "ok"}
            ],
            "report": _agent_report(incident_id, "run-ps46"),
            "llm_calls_used": 2,
        }

    monkeypatch.setattr("apps.agent.graph.run_pipeline", _fake_pipeline)
    response = api_client.post(
        "/runs",
        json={
            "incident_id": "inc-ps46",
            "payload": {"time_range_start": "2025-02-14T09:00:00Z"},
        },
    )
    assert response.status_code == 200
    metrics = api_client.get("/metrics")
    assert metrics.status_code == 200
    body = metrics.text
    assert "agent_behavior_runs_total" in body
    assert "agent_escalations_total" in body
    assert 'reason="no_evidence"' in body
    assert "agent_evidence_coverage_total" in body
    assert "agent_stage_duration_seconds" in body
