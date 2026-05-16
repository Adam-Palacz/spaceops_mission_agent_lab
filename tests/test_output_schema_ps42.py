from __future__ import annotations

import pytest

from apps.agent.graph import _run_timeout_escalation_result
from apps.agent.nodes import report
from apps.contracts.output_validation import (
    OUTPUT_SCHEMA_VIOLATION,
    OutputSchemaViolation,
    validate_escalation_packet,
    validate_run_report,
)


def _valid_report_state(**overrides: object) -> dict:
    base = {
        "incident_id": "ps42-pass",
        "subsystem": "Power",
        "risk": "medium",
        "hypotheses": ["Telemetry indicates voltage ripple."],
        "citations": [
            {"doc_id": "rb-power", "snippet_id": "s1", "content": "Power runbook note."}
        ],
        "plan": [
            {
                "action": "Create ticket for power team",
                "action_type": "create_ticket",
                "safe": True,
                "doc_ids": ["rb-power"],
                "snippet_ids": ["s1"],
            }
        ],
        "escalated": False,
        "trace_id": "a" * 32,
    }
    base.update(overrides)
    return base


def test_ps42_valid_report_passes_strict_validation():
    out = report(_valid_report_state(run_id="run-ps42-pass"))
    rep = out.get("report") or {}
    assert out.get("output_schema_status") == "ok"
    assert rep.get("schema_version") == "v1"
    assert rep.get("run_id") == "run-ps42-pass"
    assert validate_run_report(rep)


def test_ps42_run_timeout_report_matches_agent_report_v1():
    result = _run_timeout_escalation_result("inc-timeout", "a" * 32, "run-timeout-1")
    rep = result.get("report") or {}
    assert rep.get("schema_version") == "v1"
    assert rep.get("run_id") == "run-timeout-1"
    validate_run_report(rep)


def test_ps42_invalid_escalation_packet_fails_closed():
    state = _valid_report_state(
        escalated=True,
        escalation_packet={
            "reason": "",
            "what_we_know": [],
            "what_we_dont_know": [],
            "what_to_check": [],
        },
    )
    out = report(state)
    rep = out.get("report") or {}
    packet = rep.get("escalation_packet") or {}
    assert out.get("escalated") is True
    assert out.get("output_schema_status") == "violation"
    assert out.get("output_schema_reason") == OUTPUT_SCHEMA_VIOLATION
    assert packet.get("reason") == OUTPUT_SCHEMA_VIOLATION
    validate_run_report(rep)


def test_ps42_invalid_act_results_fails_closed():
    state = _valid_report_state(
        act_results=[{"step_index": 0, "unexpected": True}],
    )
    out = report(state)
    rep = out.get("report") or {}
    assert out.get("output_schema_status") == "violation"
    assert (rep.get("escalation_packet") or {}).get("reason") == OUTPUT_SCHEMA_VIOLATION
    validate_run_report(rep)


def test_ps42_validate_run_report_rejects_unknown_fields():
    payload = {
        "schema_version": "v1",
        "incident_id": "x",
        "run_id": "run-x",
        "executive_summary": "summary",
        "evidence": [{"hypothesis": "h"}],
        "citation_refs": [],
        "proposed_actions": [],
        "rollback": "rb",
        "trace_link": "",
        "extra_field": True,
    }
    with pytest.raises(OutputSchemaViolation) as exc_info:
        validate_run_report(payload)
    assert exc_info.value.envelope == "report"
    assert exc_info.value.reason_code == OUTPUT_SCHEMA_VIOLATION


def test_ps42_validate_escalation_packet_requires_reason():
    with pytest.raises(OutputSchemaViolation):
        validate_escalation_packet(
            {
                "reason": "",
                "what_we_know": ["a"],
                "what_we_dont_know": ["b"],
                "what_to_check": ["c"],
            }
        )
