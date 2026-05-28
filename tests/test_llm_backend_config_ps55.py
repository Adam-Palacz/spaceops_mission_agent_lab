"""PS5.5 — Backend config/rollout policy tests."""

from __future__ import annotations

import logging

import pytest

from apps.llm_backends.registry import (
    reset_backend_warnings_for_tests,
    resolve_llm_backend,
)
from apps.llm_gateway_errors import LLMGatewayProviderError


@pytest.fixture(autouse=True)
def _reset_warnings():
    reset_backend_warnings_for_tests()
    yield
    reset_backend_warnings_for_tests()


def test_ps55_unknown_llm_backend_raises_clear_error(monkeypatch):
    monkeypatch.setattr("config.settings.llm_backend", "something-else")
    monkeypatch.setattr("config.settings.llm_provider", "")
    with pytest.raises(LLMGatewayProviderError, match="Unsupported LLM_BACKEND"):
        resolve_llm_backend()


def test_ps55_unset_defaults_to_openai(monkeypatch):
    monkeypatch.setattr("config.settings.llm_backend", "")
    monkeypatch.setattr("config.settings.llm_provider", "")
    assert resolve_llm_backend() == "openai"


def test_ps55_provider_only_routes_cursor_with_deprecation(monkeypatch, caplog):
    monkeypatch.setattr("config.settings.llm_backend", "")
    monkeypatch.setattr("config.settings.llm_provider", "cursor_sh")
    with caplog.at_level(logging.WARNING):
        assert resolve_llm_backend() == "cursor_sh"
    assert "deprecated" in caplog.text.lower()


def test_ps55_backend_wins_on_conflict(monkeypatch, caplog):
    monkeypatch.setattr("config.settings.llm_backend", "gpu")
    monkeypatch.setattr("config.settings.llm_provider", "cursor_sh")
    with caplog.at_level(logging.WARNING):
        assert resolve_llm_backend() == "gpu"
    assert "ignored" in caplog.text.lower()
