"""GPU / NIM backend adapter (PS5.3)."""

from __future__ import annotations

from typing import Any

from config import settings

from apps.llm_backends._settings import chat_completions_path, llm_timeout_seconds
from apps.llm_backends.http_common import (
    chat_completion,
    normalize_chat_url,
    parse_chat_response,
)
from apps.llm_backends.nim_client import BACKEND_ID, record_gpu_activity
from apps.llm_gateway_errors import LLMGatewayProviderError


def resolve_gpu_model_id(model_id: str) -> str:
    """NIM model id from GPU_LLM_MODEL_ID; agent model_id is fallback only."""
    resolved = (getattr(settings, "gpu_llm_model_id", "") or "").strip() or (
        model_id or ""
    ).strip()
    if not resolved:
        raise LLMGatewayProviderError(
            "GPU_LLM_MODEL_ID or model_id required when LLM_BACKEND=gpu."
        )
    return resolved


def generate_gpu(
    *,
    prompt: str,
    model_id: str,
    temperature: float,
) -> dict[str, Any]:
    base = (getattr(settings, "gpu_llm_base_url", "") or "").strip()
    if not base:
        raise LLMGatewayProviderError(
            "GPU_LLM_BASE_URL required when LLM_BACKEND=gpu; start NIM profile (PS5.3)."
        )
    resolved_model = resolve_gpu_model_id(model_id)
    api_key = (getattr(settings, "gpu_llm_api_key", "") or "").strip()
    endpoint = normalize_chat_url(base, chat_completions_path())
    data, latency_ms = chat_completion(
        endpoint=endpoint,
        api_key=api_key,
        model_id=resolved_model,
        prompt=prompt,
        temperature=temperature,
        timeout_s=llm_timeout_seconds(),
    )
    content, usage = parse_chat_response(data)
    record_gpu_activity()
    return {
        "content": content,
        "usage": usage,
        "latency_ms": latency_ms,
        "backend_actual": BACKEND_ID,
        "model_id": resolved_model,
        "estimated_cost_usd": 0.0,
    }
