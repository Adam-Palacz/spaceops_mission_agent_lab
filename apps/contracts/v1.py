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
    schema_version: Literal["v1"] = "v1"
    incident_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    summary: str = Field(default="")
    subsystem: str = Field(default="")
    risk: str = Field(default="")
    plan: list[dict[str, Any]] = Field(default_factory=list)
    citation_refs: list[str] = Field(default_factory=list)
    escalated: bool = Field(default=False)
    trace_url: str | None = None


class EscalationPacketV1(ContractBase):
    schema_version: Literal["v1"] = "v1"
    incident_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    what_we_know: list[str] = Field(default_factory=list)
    what_we_dont_know: list[str] = Field(default_factory=list)
    what_to_check: list[str] = Field(default_factory=list)
    citations: list[CitationV1] = Field(default_factory=list)
