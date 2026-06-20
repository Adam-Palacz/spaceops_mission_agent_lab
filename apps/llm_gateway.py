"""
LLM gateway contract (PS1.6, PS5.1).

Single entry point for agent/eval LLM calls; backends live in apps.llm_backends.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from prometheus_client import Counter

from config import settings
from apps.llm_backends.resilience import (
    can_use_gpu_backend,
    mark_gpu_backend_failure,
    mark_gpu_backend_success,
)
from apps.llm_cost import enforce_budget_before_generate, record_llm_usage
from apps.llm_backends.registry import get_backend_generator, resolve_llm_backend
from apps.llm_gateway_errors import (
    LLMBudgetExceededError,
    LLMGatewayProviderError,
    LLMGatewayTimeoutError,
)
from apps.llm_provenance import record_gateway_provenance
from apps.llm_burst_routing import (
    BurstRoutingSignals,
    decide_burst_route,
    explain_gateway_routing_reason,
)
from apps.model_selection import get_current_model_id

_logger = logging.getLogger(__name__)

LLM_BACKEND_FALLBACK_TOTAL = Counter(
    "llm_backend_fallback_total",
    "LLM backend fallbacks by backend pair and reason (PS5.4).",
    ["from_backend", "to_backend", "reason"],
)

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
      backend_routing_reason (PS7.7)
    """
    resolved_model = (model_id or "").strip() or get_current_model_id()
    started = time.perf_counter()
    backend_requested = "unresolved"
    fallback_used = False
    fallback_reason = ""
    try:
        enforce_budget_before_generate(node=node)
        backend_requested = resolve_llm_backend()
        raw: dict[str, Any]
        if backend_requested != "gpu":
            backend_fn = get_backend_generator(backend_requested)
            raw = backend_fn(
                prompt=prompt,
                model_id=resolved_model,
                temperature=temperature,
            )
        else:
            can_use, preflight_reason = can_use_gpu_backend()
            if not can_use:
                fallback_used = True
                fallback_reason = preflight_reason
                raw = _fallback_to_openai_or_raise(
                    prompt=prompt,
                    model_id=resolved_model,
                    temperature=temperature,
                    fallback_reason=preflight_reason,
                )
            else:
                backend_fn = get_backend_generator("gpu")
                try:
                    raw = backend_fn(
                        prompt=prompt,
                        model_id=resolved_model,
                        temperature=temperature,
                    )
                    mark_gpu_backend_success()
                except LLMBudgetExceededError:
                    raise
                except LLMGatewayTimeoutError:
                    mark_gpu_backend_failure()
                    fallback_used = True
                    fallback_reason = "gpu_timeout"
                    raw = _fallback_to_openai_or_raise(
                        prompt=prompt,
                        model_id=resolved_model,
                        temperature=temperature,
                        fallback_reason=fallback_reason,
                    )
                except LLMGatewayProviderError:
                    mark_gpu_backend_failure()
                    fallback_used = True
                    fallback_reason = "gpu_error"
                    raw = _fallback_to_openai_or_raise(
                        prompt=prompt,
                        model_id=resolved_model,
                        temperature=temperature,
                        fallback_reason=fallback_reason,
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
    backend_routing_reason = _resolve_backend_routing_reason(
        backend_requested=backend_requested,
        backend_actual=backend_actual,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
    )
    record_llm_usage(
        node=node,
        backend_actual=backend_actual,
        model_id=out_model,
        total_tokens=int(usage.get("total_tokens") or 0),
        estimated_cost_usd=estimated_cost,
    )
    _logger.info(
        "llm_gateway_call node=%s provider=%s backend_requested=%s backend_actual=%s "
        "outcome=success model_id=%s latency_ms=%d total_tokens=%d "
        "fallback_used=%s fallback_reason=%s backend_routing_reason=%s estimated_cost_usd=%.6f",
        node,
        backend_actual,
        backend_requested,
        backend_actual,
        out_model,
        latency_ms,
        int(usage.get("total_tokens") or 0),
        fallback_used,
        fallback_reason,
        backend_routing_reason,
        estimated_cost,
    )
    record_gateway_provenance(
        node=node,
        backend_requested=backend_requested,
        backend_actual=backend_actual,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        backend_routing_reason=backend_routing_reason,
    )
    return {
        "content": str(raw.get("content") or ""),
        "model_id": out_model,
        "provider": backend_actual,
        "latency_ms": latency_ms,
        "usage": usage,
        "backend_requested": backend_requested,
        "backend_actual": backend_actual,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "backend_routing_reason": backend_routing_reason,
        "estimated_cost_usd": estimated_cost,
    }


def _resolve_backend_routing_reason(
    *,
    backend_requested: str,
    backend_actual: str,
    fallback_used: bool,
    fallback_reason: str,
) -> str:
    if not getattr(settings, "llm_burst_routing_audit", True):
        return ""

    kill_switch = bool(getattr(settings, "llm_burst_kill_switch", False))
    policy_reason: str | None = None

    if getattr(settings, "llm_burst_enabled", False) and not kill_switch:
        from apps.llm_backends.resilience import can_use_gpu_backend

        burst_healthy = True
        if (getattr(settings, "llm_burst_backend", "gpu") or "gpu").strip() == "gpu":
            burst_healthy, _ = can_use_gpu_backend()

        policy = decide_burst_route(
            BurstRoutingSignals(
                kill_switch=False,
                burst_enabled=True,
                primary_backend="openai",
                burst_backend=str(
                    getattr(settings, "llm_burst_backend", "gpu") or "gpu"
                ),
                primary_healthy=True,
                burst_healthy=burst_healthy,
                budget_ok=True,
                burst_within_cost_ceiling=True,
                burst_latency_p95_ms=None,
                latency_sla_ms=int(
                    getattr(settings, "llm_burst_latency_sla_ms", 2000) or 2000
                ),
            )
        )
        policy_reason = policy.backend_routing_reason

    return explain_gateway_routing_reason(
        backend_requested=backend_requested,
        backend_actual=backend_actual,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        kill_switch=kill_switch,
        burst_policy_reason=policy_reason,
    )


def _fallback_to_openai_or_raise(
    *,
    prompt: str,
    model_id: str,
    temperature: float,
    fallback_reason: str,
) -> dict[str, Any]:
    openai_api_key = (getattr(settings, "openai_api_key", "") or "").strip()
    if not openai_api_key:
        raise LLMGatewayProviderError(
            "GPU backend unavailable and OPENAI_API_KEY missing; cannot fallback to openai."
        )
    LLM_BACKEND_FALLBACK_TOTAL.labels(
        from_backend="gpu", to_backend="openai", reason=fallback_reason
    ).inc()
    openai_fn = get_backend_generator("openai")
    return openai_fn(
        prompt=prompt,
        model_id=model_id,
        temperature=temperature,
    )
