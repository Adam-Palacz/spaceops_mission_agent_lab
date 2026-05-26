"""PS5.2 — OpenAI backend adapter contract and parity baseline tests."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx
import pytest

from apps.llm_backends.openai import (
    BACKEND_ID,
    PARITY_METADATA_KEYS,
    estimate_cost_usd,
    generate_openai,
    parse_openai_completion,
)
from apps.llm_backends.registry import (
    reset_backend_warnings_for_tests,
    resolve_llm_backend,
)
from apps.llm_gateway import generate
from apps.llm_gateway_errors import LLMGatewayProviderError

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "llm"


@pytest.fixture(autouse=True)
def _reset_warnings():
    reset_backend_warnings_for_tests()
    yield
    reset_backend_warnings_for_tests()


def _load_json(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def test_parity_metadata_baseline_fixture_documents_keys():
    baseline = _load_json("openai_parity_metadata_baseline.json")
    assert baseline["backend_arm"] == "openai"
    assert set(baseline["required_response_keys"]) == PARITY_METADATA_KEYS


def test_parse_openai_completion_golden_fixture():
    data = _load_json("openai_chat_completion.json")
    content, usage = parse_openai_completion(data)
    assert "Power" in content
    assert usage == {
        "prompt_tokens": 42,
        "completion_tokens": 12,
        "total_tokens": 54,
    }


def test_parse_openai_completion_empty_choices():
    content, usage = parse_openai_completion({"choices": [], "usage": {}})
    assert content == ""
    assert usage["total_tokens"] == 0


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "expected JSON object"),
        ({"choices": "bad"}, "choices must be a list"),
        ({"choices": [{}]}, "message must be an object"),
        ({"choices": [{"message": []}]}, "message must be an object"),
        (
            {"choices": [], "usage": {"total_tokens": "bad"}},
            "token usage must be numeric",
        ),
    ],
)
def test_parse_openai_completion_invalid_shape_raises_provider_error(payload, message):
    with pytest.raises(LLMGatewayProviderError, match=message):
        parse_openai_completion(payload)


def test_estimate_cost_zero_when_rate_unset(monkeypatch):
    monkeypatch.setattr("config.settings.llm_openai_cost_per_1k_tokens", 0.0)
    assert estimate_cost_usd({"total_tokens": 1000}) == 0.0


def test_estimate_cost_with_rate_card(monkeypatch):
    monkeypatch.setattr("config.settings.llm_openai_cost_per_1k_tokens", 0.5)
    assert estimate_cost_usd({"total_tokens": 2000}) == 1.0


def test_legacy_llm_provider_openai_only_routes_to_openai(monkeypatch):
    monkeypatch.setattr("config.settings.llm_backend", "")
    monkeypatch.setattr("config.settings.llm_provider", "openai")
    assert resolve_llm_backend() == BACKEND_ID


def test_generate_openai_missing_api_key(monkeypatch):
    monkeypatch.setattr("config.settings.openai_api_key", "")
    with pytest.raises(LLMGatewayProviderError, match="OPENAI_API_KEY"):
        generate_openai(prompt="x", model_id="gpt-4o-mini", temperature=0)


def test_generate_openai_http_mock(monkeypatch):
    fixture = _load_json("openai_chat_completion.json")
    calls: list[dict] = []

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return fixture

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, _url, **kwargs):
            calls.append(kwargs.get("json") or {})
            return _Resp()

    monkeypatch.setattr("apps.llm_backends.http_common.httpx.Client", _Client)
    monkeypatch.setattr("config.settings.openai_api_key", "sk-test")
    monkeypatch.setattr("config.settings.openai_base_url", "https://api.openai.com")
    monkeypatch.setattr("config.settings.llm_openai_cost_per_1k_tokens", 0.01)

    raw = generate_openai(prompt="classify", model_id="gpt-4o-mini", temperature=0)
    assert raw["backend_actual"] == BACKEND_ID
    assert raw["content"] == fixture["choices"][0]["message"]["content"]
    assert raw["estimated_cost_usd"] == round(54 / 1000.0 * 0.01, 6)
    assert calls[0]["model"] == "gpt-4o-mini"
    assert calls[0]["messages"][0]["content"] == "classify"


def test_gateway_openai_includes_metadata_and_log_shape(caplog, monkeypatch):
    fixture = _load_json("openai_chat_completion.json")

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return fixture

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return _Resp()

    monkeypatch.setattr("apps.llm_backends.http_common.httpx.Client", _Client)
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr("config.settings.openai_api_key", "sk-test")
    monkeypatch.setattr("config.settings.llm_openai_cost_per_1k_tokens", 0.0)

    with caplog.at_level(logging.INFO):
        out = generate(prompt="p", node="triage", model_id="gpt-4o-mini")

    assert out["backend_requested"] == "openai"
    assert out["backend_actual"] == "openai"
    assert out["estimated_cost_usd"] == 0.0
    assert set(out.keys()) >= PARITY_METADATA_KEYS
    assert any("llm_gateway_call" in r.message for r in caplog.records)
    assert any("provider=openai" in r.message for r in caplog.records)
    assert any("backend_actual=openai" in r.message for r in caplog.records)
    assert any("outcome=success" in r.message for r in caplog.records)
    assert any("estimated_cost_usd=" in r.message for r in caplog.records)


def test_chat_completion_malformed_json_raises_provider_error(monkeypatch):
    class _BadJsonResp:
        def raise_for_status(self):
            return None

        def json(self):
            raise ValueError("not json")

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return _BadJsonResp()

    monkeypatch.setattr("apps.llm_backends.http_common.httpx.Client", _Client)
    monkeypatch.setattr("config.settings.openai_api_key", "sk-test")
    with pytest.raises(LLMGatewayProviderError, match="not json"):
        generate_openai(prompt="x", model_id="m", temperature=0)


def test_chat_completion_timeout_raises_timeout_error(monkeypatch):
    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            raise httpx.TimeoutException("slow")

    monkeypatch.setattr("apps.llm_backends.http_common.httpx.Client", _Client)
    monkeypatch.setattr("config.settings.openai_api_key", "sk-test")
    from apps.llm_gateway_errors import LLMGatewayTimeoutError

    with pytest.raises(LLMGatewayTimeoutError):
        generate_openai(prompt="x", model_id="m", temperature=0)


def test_gateway_failure_logs_attempted_backend_without_claiming_served_call(
    caplog, monkeypatch
):
    class _BadShapeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return []

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return _BadShapeResp()

    monkeypatch.setattr("apps.llm_backends.http_common.httpx.Client", _Client)
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr("config.settings.openai_api_key", "sk-test")

    with caplog.at_level(logging.WARNING):
        with pytest.raises(LLMGatewayProviderError, match="expected JSON object"):
            generate(prompt="p", node="triage", model_id="gpt-4o-mini")

    assert any("provider=openai" in r.message for r in caplog.records)
    assert any("backend_requested=openai" in r.message for r in caplog.records)
    assert any("backend_actual=unserved" in r.message for r in caplog.records)
    assert any("outcome=error" in r.message for r in caplog.records)


def test_gateway_invalid_backend_failure_is_logged(caplog, monkeypatch):
    monkeypatch.setattr("config.settings.llm_backend", "invalid")
    monkeypatch.setattr("config.settings.llm_provider", "")

    with caplog.at_level(logging.WARNING):
        with pytest.raises(LLMGatewayProviderError, match="Unsupported LLM_BACKEND"):
            generate(prompt="p", node="triage", model_id="gpt-4o-mini")

    assert any("backend_requested=unresolved" in r.message for r in caplog.records)
    assert any("backend_actual=unserved" in r.message for r in caplog.records)
    assert any("outcome=error" in r.message for r in caplog.records)
