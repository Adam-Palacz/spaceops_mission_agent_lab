from __future__ import annotations

from apps.contracts.v1 import (
    AgentReportV1,
    EscalationPacketV1,
    IncidentV1,
    TelemetryEventV1,
)


def test_telemetry_event_v1_validates_required_fields() -> None:
    item = TelemetryEventV1(
        event_id="evt-1",
        ts="2025-02-14T10:00:00Z",
        channel="bus_voltage",
        value=27.8,
    )
    assert item.schema_version == "v1"
    assert item.source == "telemetry"


def test_incident_v1_rejects_extra_fields() -> None:
    try:
        IncidentV1(incident_id="inc-1", payload={}, unexpected=True)  # type: ignore[arg-type]
    except Exception as exc:
        assert "extra_forbidden" in str(exc)
    else:
        raise AssertionError("Expected validation error for extra field")


def test_agent_report_v1_has_expected_schema_version() -> None:
    report = AgentReportV1(
        incident_id="inc-1",
        run_id="run-1",
        executive_summary="Incident inc-1: ok.",
        evidence=[],
        rollback="N/A",
        trace_link="",
    )
    assert report.schema_version == "v1"
    assert report.executive_summary == "Incident inc-1: ok."


def test_escalation_packet_v1_requires_reason() -> None:
    try:
        EscalationPacketV1(incident_id="inc-1", run_id="run-1", reason="")
    except Exception as exc:
        assert "String should have at least 1 character" in str(exc)
    else:
        raise AssertionError("Expected validation error for empty reason")


def test_contract_schemas_embed_v1_literal() -> None:
    schema = TelemetryEventV1.model_json_schema()
    version_prop = schema["properties"]["schema_version"]
    assert version_prop.get("const") == "v1"
