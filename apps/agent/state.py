"""
SpaceOps Agent — pipeline state schema (S1.7, S1.8).
NF5a: plan steps must reference doc_id or snippet (citation grounding).
F10: escalation packet when low confidence, no evidence, conflicting signals, timeout.
"""
from __future__ import annotations

from typing import TypedDict


class Citation(TypedDict, total=False):
    doc_id: str
    snippet_id: str
    content: str


class PlanStep(TypedDict, total=False):
    action: str
    safe: bool
    doc_ids: list[str]
    snippet_ids: list[str]


class EscalationPacket(TypedDict, total=False):
    reason: str
    what_we_know: list[str]
    what_we_dont_know: list[str]
    what_to_check: list[str]


class AgentState(TypedDict, total=False):
    incident_id: str
    payload: dict
    subsystem: str
    risk: str
    hypotheses: list[str]
    citations: list[Citation]
    plan: list[PlanStep]
    report: dict
    escalated: bool
    escalation_packet: EscalationPacket
