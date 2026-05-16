"""Compatibility aliases for PS4.2 runtime envelope names.

Canonical definitions live in apps.contracts.v1 so schema export, API validation,
and pipeline outputs share one source of truth.
"""

from __future__ import annotations

from apps.contracts.v1 import (
    AgentReportV1,
    ApprovalRequestV1,
    EmbeddedEscalationPacketV1,
    EvidenceItemV1,
    ToolResultV1,
)

EscalationPacketEnvelope = EmbeddedEscalationPacketV1
EvidenceItemEnvelope = EvidenceItemV1
ToolResultEnvelope = ToolResultV1
ApprovalRequestEnvelope = ApprovalRequestV1
AgentRunReportEnvelope = AgentReportV1
