"""
SpaceOps Agent — pipeline state schema (S1.7).
NF5a: plan steps must reference doc_id or snippet (citation grounding).
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


class AgentState(TypedDict, total=False):
    incident_id: str
    payload: dict
    subsystem: str
    risk: str
    hypotheses: list[str]
    citations: list[Citation]
    plan: list[PlanStep]
    report: dict
