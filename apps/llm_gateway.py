"""
LLM gateway contract (PS1.6, PS5.1).

Single entry point for agent/eval LLM calls; backends live in apps.llm_backends.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from apps.llm_backends.registry import get_backend_generator, resolve_llm_backend
from apps.llm_gateway_errors import (
    LLMBudgetExceededError,
    LLMGatewayProviderError,
    LLMGatewayTimeoutError,
)
from apps.model_selection import get_current_model_id

_logger = logging.getLogger(__name__)

__all__ = [
    "LLMBudgetExceededError",
    "LLMGatewayProviderError",
    "LLMGatewayTimeoutError",
    "generate",
]


def generate(
    *,
    prompt: str,
    node: str,
    model_id: str | None = None,
    temperature: float = 0,
    trace_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Execute a chat completion via the configured backend and return normalized output.

    Returns:
      content, model_id, provider (alias of backend_actual), latency_ms, usage,
      backend_requested, backend_actual, fallback_used, fallback_reason
    """
    resolved_model = (model_id or "").strip() or get_current_model_id()
    started = time.perf_counter()
    backend_requested = "unresolved"
    try:
        backend_requested = resolve_llm_backend()
        backend_fn = get_backend_generator(backend_requested)
        raw = backend_fn(
            prompt=prompt,
            model_id=resolved_model,
            temperature=temperature,
        )
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _logger.warning(
            "llm_gateway_call node=%s provider=%s backend_requested=%s "
            "backend_actual=unserved outcome=error error_type=%s model_id=%s "
            "latency_ms=%d total_tokens=0 estimated_cost_usd=0.000000",
            node,
            backend_requested,
            backend_requested,
            type(exc).__name__,
            resolved_model,
            latency_ms,
        )
        raise
    backend_actual = str(raw.get("backend_actual") or backend_requested)
    out_model = str(raw.get("model_id") or resolved_model)
    usage = raw.get("usage") or {}
    latency_ms = int(raw.get("latency_ms") or 0)

    if trace_context:
        _logger.debug(
            "llm_gateway trace_context keys=%s",
            sorted(trace_context.keys()),
        )

    estimated_cost = float(raw.get("estimated_cost_usd") or 0)
    _logger.info(
        "llm_gateway_call node=%s provider=%s backend_requested=%s backend_actual=%s "
        "outcome=success model_id=%s latency_ms=%d total_tokens=%d estimated_cost_usd=%.6f",
        node,
        backend_actual,
        backend_requested,
        backend_actual,
        out_model,
        latency_ms,
        int(usage.get("total_tokens") or 0),
        estimated_cost,
    )
    return {
        "content": str(raw.get("content") or ""),
        "model_id": out_model,
        "provider": backend_actual,
        "latency_ms": latency_ms,
        "usage": usage,
        "backend_requested": backend_requested,
        "backend_actual": backend_actual,
        "fallback_used": False,
        "fallback_reason": "",
        "estimated_cost_usd": estimated_cost,
    }
