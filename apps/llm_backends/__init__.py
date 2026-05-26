"""LLM backend adapters (PS5.1+)."""

from apps.llm_backends.registry import resolve_llm_backend

__all__ = ["resolve_llm_backend"]
