"""
LLM gateway minimum contract (PS1.6).

Consolidates provider-specific chat completion calls behind a single interface.
Default backend remains OpenAI-compatible.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urljoin

import httpx

from config import settings
from apps.model_selection import get_current_model_id

_logger = logging.getLogger(__name__)


class LLMGatewayTimeoutError(Exception):
    """Raised when upstream LLM call times out."""


class LLMGatewayProviderError(Exception):
    """Raised when upstream LLM provider returns a non-timeout error."""


def _normalize_chat_url(base_url: str, chat_path: str) -> str:
    base = (base_url or "").strip()
    path = (chat_path or "").strip() or "/v1/chat/completions"
    if not path.startswith("/"):
        path = f"/{path}"
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/"):
        return urljoin(base, path.lstrip("/"))
    return f"{base}{path}"


def _provider_config() -> tuple[str, str, str]:
    provider = (getattr(settings, "llm_provider", "openai") or "openai").strip().lower()
    chat_path = getattr(settings, "llm_chat_completions_path", "/v1/chat/completions")
    providers = {
        "openai": {
            "api_key": (getattr(settings, "openai_api_key", "") or "").strip(),
            "base_url": (getattr(settings, "openai_base_url", "") or "").strip()
            or "https://api.openai.com",
            "missing_key_msg": "OPENAI_API_KEY required for agent; set in .env",
        },
        "cursor_sh": {
            "api_key": (getattr(settings, "cursor_sh_api_key", "") or "").strip(),
            "base_url": (getattr(settings, "cursor_sh_base_url", "") or "").strip()
            or "https://api.cursor.sh",
            "missing_key_msg": "CURSOR_SH_API_KEY required when LLM_PROVIDER=cursor_sh; set it in .env",
        },
    }
    cfg = providers.get(provider)
    if cfg is None:
        raise LLMGatewayProviderError(
            f"Unsupported LLM_PROVIDER='{provider}'. Supported: {sorted(providers.keys())}"
        )
    if not cfg["api_key"]:
        raise LLMGatewayProviderError(cfg["missing_key_msg"])
    endpoint = _normalize_chat_url(str(cfg["base_url"]), str(chat_path))
    return provider, endpoint, str(cfg["api_key"])


def generate(
    *,
    prompt: str,
    node: str,
    model_id: str | None = None,
    temperature: float = 0,
) -> dict[str, Any]:
    """
    Execute a chat completion call via configured provider and return normalized output.

    Returns:
      {
        "content": str,
        "model_id": str,
        "provider": str,
        "latency_ms": int,
        "usage": {
            "prompt_tokens": int,
            "completion_tokens": int,
            "total_tokens": int
        }
      }
    """
    resolved_model = (model_id or "").strip() or get_current_model_id()
    provider, endpoint, api_key = _provider_config()
    timeout_s = max(1, getattr(settings, "agent_llm_call_timeout_seconds", 30))
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=float(timeout_s)) as client:
            resp = client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": resolved_model,
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

    usage_raw = data.get("usage") or {}
    usage = {
        "prompt_tokens": int(usage_raw.get("prompt_tokens") or 0),
        "completion_tokens": int(usage_raw.get("completion_tokens") or 0),
        "total_tokens": int(usage_raw.get("total_tokens") or 0),
    }
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    latency_ms = int((time.perf_counter() - started) * 1000)
    _logger.info(
        "llm_gateway_call node=%s provider=%s model_id=%s latency_ms=%d total_tokens=%d",
        node,
        provider,
        resolved_model,
        latency_ms,
        usage["total_tokens"],
    )
    return {
        "content": content,
        "model_id": resolved_model,
        "provider": provider,
        "latency_ms": latency_ms,
        "usage": usage,
    }
