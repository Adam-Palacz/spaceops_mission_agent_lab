from __future__ import annotations

import httpx
import pytest

from apps.llm_gateway import (
    LLMGatewayProviderError,
    LLMGatewayTimeoutError,
    generate,
)


def test_gateway_generate_success(monkeypatch):
    calls: list[tuple] = []

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "Power medium"}}],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 8,
                    "total_tokens": 20,
                },
            }

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            calls.append((args, kwargs))
            return _Resp()

    monkeypatch.setattr("apps.llm_backends.http_common.httpx.Client", _Client)
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr("config.settings.llm_provider", "openai")
    monkeypatch.setattr("config.settings.openai_base_url", "https://api.openai.com")
    monkeypatch.setattr(
        "config.settings.llm_chat_completions_path", "/v1/chat/completions"
    )
    out = generate(prompt="x", node="triage", model_id="gpt-4o-mini")
    assert out["content"] == "Power medium"
    assert out["usage"]["total_tokens"] == 20
    assert out["model_id"] == "gpt-4o-mini"
    assert out["backend_requested"] == "openai"
    assert out["backend_actual"] == "openai"
    assert out["fallback_used"] is False
    assert calls, "gateway should issue exactly one HTTP call"
    endpoint = calls[0][0][0]
    assert endpoint == "https://api.openai.com/v1/chat/completions"


def test_gateway_generate_timeout(monkeypatch):
    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("apps.llm_backends.http_common.httpx.Client", _Client)
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    with pytest.raises(LLMGatewayTimeoutError):
        generate(prompt="x", node="decide")


def test_gateway_generate_provider_error(monkeypatch):
    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            raise RuntimeError("provider boom")

    monkeypatch.setattr("apps.llm_backends.http_common.httpx.Client", _Client)
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    with pytest.raises(LLMGatewayProviderError):
        generate(prompt="x", node="decide")


def test_gateway_uses_custom_base_url_for_cursor(monkeypatch):
    calls: list[tuple] = []

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"total_tokens": 1},
            }

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            calls.append((args, kwargs))
            return _Resp()

    monkeypatch.setattr("apps.llm_backends.http_common.httpx.Client", _Client)
    monkeypatch.setattr("config.settings.llm_backend", "")
    monkeypatch.setattr("config.settings.llm_provider", "cursor_sh")
    monkeypatch.setattr("config.settings.cursor_sh_api_key", "cursor-key")
    monkeypatch.setattr(
        "config.settings.cursor_sh_base_url", "https://gateway.internal"
    )
    monkeypatch.setattr(
        "config.settings.llm_chat_completions_path", "/v1/chat/completions"
    )
    out = generate(prompt="x", node="decide")
    assert out["provider"] == "cursor_sh"
    assert out["backend_actual"] == "cursor_sh"
    endpoint = calls[0][0][0]
    assert endpoint == "https://gateway.internal/v1/chat/completions"
