"""
PS1.1 — Contract models v1.

These models define the canonical data contracts for core operational entities.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractBase(BaseModel):
    """Base contract config: strict fields, no extras."""

    model_config = ConfigDict(extra="forbid")


class CitationV1(ContractBase):
    doc_id: str = Field(..., min_length=1)
    snippet_id: str | None = None
    content: str | None = None


class TelemetryEventV1(ContractBase):
    schema_version: Literal["v1"] = "v1"
    event_id: str = Field(..., min_length=1)
    ts: str = Field(..., min_length=1, description="ISO8601 UTC timestamp string.")
    channel: str = Field(..., min_length=1)
    value: float | int | str
    subsystem: str | None = None
    unit: str | None = None
    source: str = Field(default="telemetry", min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentV1(ContractBase):
    schema_version: Literal["v1"] = "v1"
    incident_id: str = Field(..., min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = Field(
        default=None, description="ISO8601 UTC timestamp of incident creation."
    )
    source_event_ids: list[str] = Field(default_factory=list)


class AgentReportV1(ContractBase):
    """Canonical v1 report emitted by the agent pipeline and persisted by APIs."""

    schema_version: Literal["v1"] = "v1"
    incident_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    executive_summary: str
    evidence: list["EvidenceItemV1"]
    citation_refs: list[str] = Field(default_factory=list)
    proposed_actions: list[str] = Field(default_factory=list)
    rollback: str
    trace_link: str
    act_results: list["ToolResultV1"] = Field(default_factory=list)
    approval_requests: list["ApprovalRequestV1"] = Field(default_factory=list)
    escalation_packet: "EmbeddedEscalationPacketV1 | None" = None
    handoff: str | None = None
    summary: str | None = Field(
        default=None,
        description="Deprecated compatibility alias; prefer executive_summary.",
    )


class EmbeddedEscalationPacketV1(ContractBase):
    """Escalation handoff packet embedded in agent state and reports.

    The enclosing AgentReportV1 carries incident_id/run_id/schema_version.
    """

    reason: str = Field(..., min_length=1)
    what_we_know: list[str] = Field(default_factory=list)
    what_we_dont_know: list[str] = Field(default_factory=list)
    what_to_check: list[str] = Field(default_factory=list)


class EvidenceItemV1(BaseModel):
    """Single evidence row in the run report."""

    model_config = ConfigDict(extra="ignore")

    hypothesis: str


class ToolResultV1(ContractBase):
    """Normalized Act/MCP tool result row."""

    step_index: int = Field(..., ge=0)
    tool: str = Field(..., min_length=1)
    outcome: Literal["success", "empty", "failure"]
    result: dict[str, Any] | list[Any] | str | int | float | bool | None = None


class ApprovalRequestV1(ContractBase):
    """Pending restricted-action approval created during Act."""

    id: str = Field(..., min_length=1)
    step_index: int = Field(..., ge=0)
    step: dict[str, Any]
    incident_id: str = Field(..., min_length=1)
    reason: str = Field(default="restricted", min_length=1)


class EscalationPacketV1(ContractBase):
    """Standalone storage/escalation packet contract."""

    schema_version: Literal["v1"] = "v1"
    incident_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    what_we_know: list[str] = Field(default_factory=list)
    what_we_dont_know: list[str] = Field(default_factory=list)
    what_to_check: list[str] = Field(default_factory=list)
    citations: list[CitationV1] = Field(default_factory=list)
