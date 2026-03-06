"""
SpaceOps Agent — pipeline state schema (S1.7, S1.8).
NF5a: plan steps must reference doc_id or snippet (citation grounding).
F10: escalation packet when low confidence, no evidence, conflicting signals, timeout.
"""

from __future__ import annotations

import logging
from typing import TypedDict

from config import settings


class Citation(TypedDict, total=False):
    doc_id: str
    snippet_id: str
    content: str


class PlanStep(TypedDict, total=False):
    action: str
    safe: bool
    doc_ids: list[str]
    snippet_ids: list[str]
    # S2.3: action_type routes Act (create_ticket | create_pr | change_config | report)
    action_type: str


class EscalationPacket(TypedDict, total=False):
    reason: str
    what_we_know: list[str]
    what_we_dont_know: list[str]
    what_to_check: list[str]


class AgentState(TypedDict, total=False):
    incident_id: str
    trace_id: str
    payload: dict
    tokens_used: int  # S1.12: cumulative token count for budget check
    llm_calls_used: int  # S1.12: number of LLM calls so far (rate limit per run)
    subsystem: str
    risk: str
    hypotheses: list[str]
    citations: list[Citation]
    plan: list[PlanStep]
    # S2.3 Act: results of safe actions; restricted steps pending approval
    act_results: list[dict]
    approval_requests: list[dict]
    report: dict
    escalated: bool
    escalation_packet: EscalationPacket


_logger = logging.getLogger(__name__)


def compact_history(state: AgentState) -> AgentState:
    """
    S3.3: Compact hypotheses/citations to keep context bounded for long runs.

    - agent_max_hypotheses: max number of hypotheses kept (0 = no compaction).
    - agent_max_citations: max number of citations kept (0 = no compaction).

    Returns a delta dict suitable for merging back into state; does not modify
    the input state in-place.
    """
    max_h = max(0, getattr(settings, "agent_max_hypotheses", 0))
    max_c = max(0, getattr(settings, "agent_max_citations", 0))
    if not max_h and not max_c:
        return {}

    delta: AgentState = {}
    original_h = list(state.get("hypotheses") or [])
    original_c = list(state.get("citations") or [])

    # Hypotheses compaction
    if max_h and len(original_h) > max_h:
        compacted_h = original_h[:max_h]
        delta["hypotheses"] = compacted_h
        if getattr(settings, "agent_history_compaction_debug", False):
            _logger.info(
                "agent_history_compaction: hypotheses trimmed from %d to %d",
                len(original_h),
                len(compacted_h),
            )

    # Citations compaction
    if max_c and len(original_c) > max_c:
        compacted_c = original_c[:max_c]
        delta["citations"] = compacted_c
        if getattr(settings, "agent_history_compaction_debug", False):
            _logger.info(
                "agent_history_compaction: citations trimmed from %d to %d",
                len(original_c),
                len(compacted_c),
            )

    return delta
