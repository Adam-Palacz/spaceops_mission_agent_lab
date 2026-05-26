"""Cursor.sh backend adapter."""

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
    endpoint = normalize_chat_url(base, chat_completions_path())
    data, latency_ms = chat_completion(
        endpoint=endpoint,
        api_key=api_key,
        model_id=model_id,
        prompt=prompt,
        temperature=temperature,
        timeout_s=llm_timeout_seconds(),
    )
    content, usage = parse_chat_response(data)
    return {
        "content": content,
        "usage": usage,
        "latency_ms": latency_ms,
        "backend_actual": "cursor_sh",
        "model_id": model_id,
    }
