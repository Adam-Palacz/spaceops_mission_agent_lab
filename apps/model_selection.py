"""
S3.1 — Model selection helpers for the agent.

Provides a single place to read the current production model id and any candidate
model ids for shadow-testing from config.settings.
"""

from __future__ import annotations

from typing import List

from config import settings


def get_current_model_id() -> str:
    """
    Return the current production model identifier for agent LLM calls.
    """
    value = (getattr(settings, "agent_model_id", "") or "").strip()
    return value or "gpt-4.1-nano"


def get_candidate_model_ids() -> List[str]:
    """
    Return a list of candidate model identifiers for shadow-testing.

    Parsed from settings.agent_candidate_model_ids as a comma-separated string.
    """
    raw = (getattr(settings, "agent_candidate_model_ids", "") or "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]
