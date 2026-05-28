"""PS5.3 — NIM GPU backend adapter (mocked HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.llm_backends.gpu import generate_gpu, resolve_gpu_model_id
from apps.llm_backends.nim_client import (
    NIM_HEALTH_PATH,
    check_nim_health,
    nim_health_url,
    record_gpu_activity,
)
from apps.llm_gateway import generate
from apps.llm_gateway_errors import LLMGatewayProviderError

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "llm"


def _fixture_completion() -> dict:
    return json.loads(
        (_FIXTURES / "openai_chat_completion.json").read_text(encoding="utf-8")
    )


def _mock_client(monkeypatch, payload: dict):
    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

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


def test_nim_health_url_builds():
    url = nim_health_url("http://nim.local:8005")
    assert url == f"http://nim.local:8005{NIM_HEALTH_PATH}"


def test_gpu_model_prefers_gpu_llm_model_id(monkeypatch):
    monkeypatch.setattr("config.settings.gpu_llm_model_id", "meta/llama")
    assert resolve_gpu_model_id("gpt-4o-mini") == "meta/llama"


def test_generate_gpu_uses_nim_model_in_payload(monkeypatch, tmp_path):
    _mock_client(monkeypatch, _fixture_completion())
    monkeypatch.setattr("config.settings.gpu_llm_base_url", "http://nim:8000")
    monkeypatch.setattr(
        "config.settings.gpu_llm_model_id", "qwen/qwen2.5-0.5b-instruct"
    )
    monkeypatch.setattr("config.settings.gpu_activity_file", str(tmp_path / "activity"))
    monkeypatch.setattr("config.settings.gpu_llm_api_key", "nim-token")

    captured: list[tuple[str, dict]] = []

    class _CapturingClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, **kwargs):
            captured.append((url, kwargs))
            resp = type("R", (), {})()
            resp.raise_for_status = lambda: None
            resp.json = lambda: _fixture_completion()
            return resp

    monkeypatch.setattr("apps.llm_backends.http_common.httpx.Client", _CapturingClient)

    out = generate_gpu(
        prompt="hi", model_id="agent-model-should-not-win", temperature=0
    )
    assert captured[0][0] == "http://nim:8000/v1/chat/completions"
    assert captured[0][1]["headers"]["Authorization"] == "Bearer nim-token"
    assert captured[0][1]["json"]["model"] == "qwen/qwen2.5-0.5b-instruct"
    assert out["backend_actual"] == "gpu"
    assert (tmp_path / "activity").is_file()


def test_gateway_gpu_backend_metadata(monkeypatch, tmp_path):
    _mock_client(monkeypatch, _fixture_completion())
    monkeypatch.setattr("config.settings.llm_backend", "gpu")
    monkeypatch.setattr("config.settings.gpu_llm_base_url", "http://nim:8000")
    monkeypatch.setattr("config.settings.gpu_llm_model_id", "meta/llama")
    monkeypatch.setattr("config.settings.gpu_activity_file", str(tmp_path / "act"))
    out = generate(prompt="p", node="triage", model_id="ignored")
    assert out["backend_requested"] == "gpu"
    assert out["backend_actual"] == "gpu"
    assert out["model_id"] == "meta/llama"


def test_check_nim_health_true(monkeypatch):
    class _Resp:
        status_code = 200

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url):
            return _Resp()

    monkeypatch.setattr("apps.llm_backends.nim_client.httpx.Client", _Client)
    assert check_nim_health(base_url="http://nim:8000") is True


def test_record_gpu_activity_writes_file(tmp_path, monkeypatch):
    path = tmp_path / "llm_last_gpu_call_at"
    monkeypatch.setattr("config.settings.gpu_activity_file", str(path))
    written = record_gpu_activity()
    assert written == path
    assert path.read_text(encoding="utf-8").strip()


def test_missing_gpu_base_url_raises(monkeypatch):
    monkeypatch.setattr("config.settings.gpu_llm_base_url", "")
    with pytest.raises(LLMGatewayProviderError, match="GPU_LLM_BASE_URL"):
        generate_gpu(prompt="x", model_id="m", temperature=0)
