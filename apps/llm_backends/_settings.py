"""Shared settings helpers for LLM backend adapters."""

from __future__ import annotations

from config import settings


def chat_completions_path() -> str:
    return str(getattr(settings, "llm_chat_completions_path", "/v1/chat/completions"))


def llm_timeout_seconds() -> float:
    return float(max(1, getattr(settings, "agent_llm_call_timeout_seconds", 30)))
