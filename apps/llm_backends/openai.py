"""OpenAI cloud backend adapter (PS5.2 reference implementation)."""

from __future__ import annotations

from typing import Any

from config import settings

from apps.llm_backends._settings import chat_completions_path, llm_timeout_seconds
from apps.llm_backends.http_common import (
    chat_completion,
    normalize_chat_url,
    parse_chat_response,
)
from apps.llm_gateway_errors import LLMGatewayProviderError

BACKEND_ID = "openai"

# Keys expected in gateway output / PS5.8 parity baseline (see tests/fixtures/llm/).
PARITY_METADATA_KEYS = frozenset(
    {
        "content",
        "model_id",
        "provider",
        "latency_ms",
        "usage",
        "backend_requested",
        "backend_actual",
        "fallback_used",
        "fallback_reason",
        "estimated_cost_usd",
    }
)


def estimate_cost_usd(usage: dict[str, int]) -> float:
    """
    Optional spend estimate from token usage and configured rate card.
    Returns 0.0 when LLM_OPENAI_COST_PER_1K_TOKENS is unset or zero.
    """
    rate = float(getattr(settings, "llm_openai_cost_per_1k_tokens", 0) or 0)
    if rate <= 0:
        return 0.0
    total = int(usage.get("total_tokens") or 0)
    return round((total / 1000.0) * rate, 6)


def parse_openai_completion(data: Any) -> tuple[str, dict[str, int]]:
    """Normalize OpenAI chat completion JSON (shared parser with other compatible APIs)."""
    return parse_chat_response(data)


def generate_openai(
    *,
    prompt: str,
    model_id: str,
    temperature: float,
) -> dict[str, Any]:
    api_key = (getattr(settings, "openai_api_key", "") or "").strip()
    if not api_key:
        raise LLMGatewayProviderError("OPENAI_API_KEY required for agent; set in .env")
    base = (
        getattr(settings, "openai_base_url", "") or ""
    ).strip() or "https://api.openai.com"
    endpoint = normalize_chat_url(base, chat_completions_path())
    data, latency_ms = chat_completion(
        endpoint=endpoint,
        api_key=api_key,
        model_id=model_id,
        prompt=prompt,
        temperature=temperature,
        timeout_s=llm_timeout_seconds(),
    )
    content, usage = parse_openai_completion(data)
    return {
        "content": content,
        "usage": usage,
        "latency_ms": latency_ms,
        "backend_actual": BACKEND_ID,
        "model_id": model_id,
        "estimated_cost_usd": estimate_cost_usd(usage),
    }
