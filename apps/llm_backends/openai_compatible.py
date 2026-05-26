"""OpenAI-compatible HTTP backends: openai, cursor_sh, gpu (PS5.1)."""

from __future__ import annotations

from typing import Any

from config import settings

from apps.llm_backends.http_common import (
    chat_completion,
    normalize_chat_url,
    parse_chat_response,
)
from apps.llm_gateway_errors import LLMGatewayProviderError


def _chat_path() -> str:
    return str(getattr(settings, "llm_chat_completions_path", "/v1/chat/completions"))


def _timeout_s() -> float:
    return float(max(1, getattr(settings, "agent_llm_call_timeout_seconds", 30)))


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
    endpoint = normalize_chat_url(base, _chat_path())
    data, latency_ms = chat_completion(
        endpoint=endpoint,
        api_key=api_key,
        model_id=model_id,
        prompt=prompt,
        temperature=temperature,
        timeout_s=_timeout_s(),
    )
    content, usage = parse_chat_response(data)
    return {
        "content": content,
        "usage": usage,
        "latency_ms": latency_ms,
        "backend_actual": "openai",
    }


def generate_cursor_sh(
    *,
    prompt: str,
    model_id: str,
    temperature: float,
) -> dict[str, Any]:
    api_key = (getattr(settings, "cursor_sh_api_key", "") or "").strip()
    if not api_key:
        raise LLMGatewayProviderError(
            "CURSOR_SH_API_KEY required when LLM_BACKEND=cursor_sh; set it in .env"
        )
    base = (
        getattr(settings, "cursor_sh_base_url", "") or ""
    ).strip() or "https://api.cursor.sh"
    endpoint = normalize_chat_url(base, _chat_path())
    data, latency_ms = chat_completion(
        endpoint=endpoint,
        api_key=api_key,
        model_id=model_id,
        prompt=prompt,
        temperature=temperature,
        timeout_s=_timeout_s(),
    )
    content, usage = parse_chat_response(data)
    return {
        "content": content,
        "usage": usage,
        "latency_ms": latency_ms,
        "backend_actual": "cursor_sh",
    }


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
    resolved_model = (getattr(settings, "gpu_llm_model_id", "") or "").strip() or (
        model_id or ""
    ).strip()
    if not resolved_model:
        raise LLMGatewayProviderError(
            "GPU_LLM_MODEL_ID or model_id required when LLM_BACKEND=gpu."
        )
    api_key = (getattr(settings, "gpu_llm_api_key", "") or "").strip()
    endpoint = normalize_chat_url(base, _chat_path())
    data, latency_ms = chat_completion(
        endpoint=endpoint,
        api_key=api_key,
        model_id=resolved_model,
        prompt=prompt,
        temperature=temperature,
        timeout_s=_timeout_s(),
    )
    content, usage = parse_chat_response(data)
    return {
        "content": content,
        "usage": usage,
        "latency_ms": latency_ms,
        "backend_actual": "gpu",
        "model_id": resolved_model,
    }
