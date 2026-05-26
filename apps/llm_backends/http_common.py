"""Shared OpenAI-compatible HTTP helpers for LLM backends."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin

import httpx

from apps.llm_gateway_errors import LLMGatewayProviderError, LLMGatewayTimeoutError


def normalize_chat_url(base_url: str, chat_path: str) -> str:
    base = (base_url or "").strip()
    path = (chat_path or "").strip() or "/v1/chat/completions"
    if not path.startswith("/"):
        path = f"/{path}"
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/"):
        return urljoin(base, path.lstrip("/"))
    return f"{base}{path}"


def chat_completion(
    *,
    endpoint: str,
    api_key: str,
    model_id: str,
    prompt: str,
    temperature: float,
    timeout_s: float,
) -> tuple[dict[str, Any], int]:
    """POST chat/completions; return (parsed_json, latency_ms)."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=float(timeout_s)) as client:
            resp = client.post(
                endpoint,
                headers=headers,
                json={
                    "model": model_id,
                    "temperature": temperature,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException as exc:
        raise LLMGatewayTimeoutError(str(exc)) from exc
    except Exception as exc:
        raise LLMGatewayProviderError(str(exc)) from exc
    latency_ms = int((time.perf_counter() - started) * 1000)
    return data, latency_ms


def parse_chat_response(data: dict[str, Any]) -> tuple[str, dict[str, int]]:
    usage_raw = data.get("usage") or {}
    usage = {
        "prompt_tokens": int(usage_raw.get("prompt_tokens") or 0),
        "completion_tokens": int(usage_raw.get("completion_tokens") or 0),
        "total_tokens": int(usage_raw.get("total_tokens") or 0),
    }
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    return str(content), usage
