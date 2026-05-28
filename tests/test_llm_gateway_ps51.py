"""PS5.1 — LLM backend registry, precedence, and response metadata."""

from __future__ import annotations

import logging

import pytest

from apps.llm_backends.registry import (
    reset_backend_warnings_for_tests,
    resolve_llm_backend,
)
from apps.llm_gateway import (
    LLMGatewayProviderError,
    generate,
)
from apps.llm_gateway_errors import LLMBudgetExceededError


def _mock_http_client(monkeypatch):
    calls: list[tuple] = []

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"total_tokens": 3},
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
    return calls


@pytest.fixture(autouse=True)
def _reset_registry_warnings():
    reset_backend_warnings_for_tests()
    yield
    reset_backend_warnings_for_tests()


def test_unsupported_llm_backend_raises(monkeypatch):
    monkeypatch.setattr("config.settings.llm_backend", "anthropic")
    monkeypatch.setattr("config.settings.llm_provider", "openai")
    with pytest.raises(LLMGatewayProviderError, match="Unsupported LLM_BACKEND"):
        resolve_llm_backend()


def test_llm_provider_cursor_sh_only_maps_backend(caplog, monkeypatch):
    monkeypatch.setattr("config.settings.llm_backend", "")
    monkeypatch.setattr("config.settings.llm_provider", "cursor_sh")
    with caplog.at_level(logging.WARNING):
        assert resolve_llm_backend() == "cursor_sh"
    assert "deprecated" in caplog.text.lower()


def test_no_backend_or_legacy_provider_defaults_to_openai_without_warning(
    caplog, monkeypatch
):
    monkeypatch.setattr("config.settings.llm_backend", "")
    monkeypatch.setattr("config.settings.llm_provider", "")
    with caplog.at_level(logging.WARNING):
        assert resolve_llm_backend() == "openai"
    assert "deprecated" not in caplog.text.lower()


def test_backend_set_warns_when_equal_legacy_provider_is_ignored(caplog, monkeypatch):
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr("config.settings.llm_provider", "openai")
    with caplog.at_level(logging.WARNING):
        assert resolve_llm_backend() == "openai"
    assert "ignored" in caplog.text.lower()


def test_llm_backend_gpu_ignores_provider(monkeypatch):
    calls = _mock_http_client(monkeypatch)
    monkeypatch.setattr("config.settings.llm_backend", "gpu")
    monkeypatch.setattr("config.settings.llm_provider", "cursor_sh")
    monkeypatch.setattr("config.settings.gpu_llm_base_url", "http://nim.local:8005")
    monkeypatch.setattr("config.settings.gpu_llm_model_id", "meta/llama")
    monkeypatch.setattr("config.settings.gpu_llm_api_key", "")
    monkeypatch.setattr("apps.llm_gateway.can_use_gpu_backend", lambda: (True, ""))
    monkeypatch.setattr("apps.llm_gateway.mark_gpu_backend_success", lambda: None)
    out = generate(prompt="hi", node="triage", model_id="ignored")
    assert out["backend_requested"] == "gpu"
    assert out["backend_actual"] == "gpu"
    assert out["fallback_used"] is False
    assert out["fallback_reason"] == ""
    assert calls[0][0][0] == "http://nim.local:8005/v1/chat/completions"
    assert calls[0][1]["json"]["model"] == "meta/llama"
    assert out["model_id"] == "meta/llama"


def test_generate_includes_backend_metadata_openai(monkeypatch):
    _mock_http_client(monkeypatch)
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    out = generate(prompt="x", node="decide")
    assert out["backend_requested"] == "openai"
    assert out["backend_actual"] == "openai"
    assert out["provider"] == "openai"
    assert out["fallback_used"] is False


def test_llmbudget_exceeded_error_exported():
    assert issubclass(LLMBudgetExceededError, Exception)
