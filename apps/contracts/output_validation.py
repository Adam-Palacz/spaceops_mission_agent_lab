"""
PS4.2 — Centralized strict validation for pipeline output envelopes.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from apps.contracts.v1 import (
    AgentReportV1,
    ApprovalRequestV1,
    EmbeddedEscalationPacketV1,
    ToolResultV1,
)

OUTPUT_SCHEMA_VIOLATION = "output_schema_violation"


class OutputSchemaViolation(Exception):
    """Raised when an output envelope fails strict schema validation."""

    def __init__(
        self,
        *,
        envelope: str,
        operator_message: str,
        detail: str = "",
    ) -> None:
        self.envelope = envelope
        self.operator_message = operator_message
        self.detail = detail or operator_message
        super().__init__(operator_message)

    @property
    def reason_code(self) -> str:
        return OUTPUT_SCHEMA_VIOLATION


def operator_message_from_validation_error(
    envelope: str, exc: ValidationError
) -> str:
    """Short, operator-readable summary without stack traces."""
    errors = exc.errors()
    if not errors:
        return f"{envelope} failed schema validation."
    first = errors[0]
    loc = ".".join(str(part) for part in first.get("loc", ()))
    msg = str(first.get("msg", "invalid value"))
    if loc:
        return f"{envelope}: invalid field '{loc}' ({msg})."
    return f"{envelope}: {msg}."


def validate_escalation_packet(data: object) -> dict[str, Any]:
    try:
        model = EmbeddedEscalationPacketV1.model_validate(data)
    except ValidationError as exc:
        raise OutputSchemaViolation(
            envelope="escalation_packet",
            operator_message=operator_message_from_validation_error(
                "escalation_packet", exc
            ),
            detail=exc.json(),
        ) from exc
    return model.model_dump()


def validate_tool_result(data: object) -> dict[str, Any]:
    try:
        model = ToolResultV1.model_validate(data)
    except ValidationError as exc:
        raise OutputSchemaViolation(
            envelope="tool_result",
            operator_message=operator_message_from_validation_error(
                "tool_result", exc
            ),
            detail=exc.json(),
        ) from exc
    return model.model_dump()


def validate_act_results(results: object) -> list[dict[str, Any]]:
    if results is None:
        return []
    if not isinstance(results, list):
        raise OutputSchemaViolation(
            envelope="tool_result",
            operator_message="tool_result: act_results must be a list.",
        )
    return [validate_tool_result(item) for item in results]


def validate_run_report(data: object) -> dict[str, Any]:
    try:
        model = AgentReportV1.model_validate(data)
    except ValidationError as exc:
        raise OutputSchemaViolation(
            envelope="report",
            operator_message=operator_message_from_validation_error("report", exc),
            detail=exc.json(),
        ) from exc
    return model.model_dump()


def validate_approval_requests(requests: object) -> list[dict[str, Any]]:
    if requests is None:
        return []
    if not isinstance(requests, list):
        raise OutputSchemaViolation(
            envelope="approval_request",
            operator_message="approval_request: approval_requests must be a list.",
        )
    out: list[dict[str, Any]] = []
    for item in requests:
        try:
            model = ApprovalRequestV1.model_validate(item)
        except ValidationError as exc:
            raise OutputSchemaViolation(
                envelope="approval_request",
                operator_message=operator_message_from_validation_error(
                    "approval_request", exc
                ),
                detail=exc.json(),
            ) from exc
        out.append(model.model_dump())
    return out


def escalation_packet_for_schema_violation(
    incident_id: str,
    *,
    envelope: str,
    detail: str,
) -> dict[str, Any]:
    packet = {
        "reason": OUTPUT_SCHEMA_VIOLATION,
        "what_we_know": [
            f"Incident {incident_id}",
            f"Output schema validation failed for {envelope}.",
        ],
        "what_we_dont_know": [
            "Automated output could not be trusted; manual review required.",
        ],
        "what_to_check": [
            "Review agent pipeline logs and recent code/deploy changes.",
            "Inspect validation detail in run metadata when available.",
            detail[:240] if detail else "See audit log for guardrail_escalation entries.",
        ],
    }
    return validate_escalation_packet(packet)
