from __future__ import annotations

import pytest

from apps.llm_backends import resilience
from apps.llm_gateway import LLM_BACKEND_FALLBACK_TOTAL, generate
from apps.llm_gateway_errors import (
    LLMBudgetExceededError,
    LLMGatewayProviderError,
    LLMGatewayTimeoutError,
)


def _counter_value(*, from_backend: str, to_backend: str, reason: str) -> float:
    metric = LLM_BACKEND_FALLBACK_TOTAL.labels(
        from_backend=from_backend, to_backend=to_backend, reason=reason
    )
    return float(metric._value.get())  # type: ignore[attr-defined]


def test_ps54_gpu_preflight_failure_fallbacks_to_openai(monkeypatch):
    monkeypatch.setattr("config.settings.llm_backend", "gpu")
    monkeypatch.setattr("config.settings.openai_api_key", "test-openai-key")
    monkeypatch.setattr(
        "apps.llm_gateway.can_use_gpu_backend", lambda: (False, "gpu_unhealthy")
    )
    monkeypatch.setattr(
        "apps.llm_gateway.get_backend_generator",
        lambda backend: (
            (
                lambda **_: {
                    "backend_actual": "gpu",
                    "content": "gpu",
                    "usage": {},
                    "model_id": "m",
                }
            )
            if backend == "gpu"
            else (
                lambda **_: {
                    "backend_actual": "openai",
                    "content": "fallback-ok",
                    "usage": {"total_tokens": 1},
                    "model_id": "gpt-4o-mini",
                    "latency_ms": 3,
                    "estimated_cost_usd": 0.0,
                }
            )
        ),
    )
    before = _counter_value(
        from_backend="gpu", to_backend="openai", reason="gpu_unhealthy"
    )
    out = generate(prompt="hi", node="decide", model_id="gpt-4o-mini")
    after = _counter_value(
        from_backend="gpu", to_backend="openai", reason="gpu_unhealthy"
    )
    assert out["backend_requested"] == "gpu"
    assert out["backend_actual"] == "openai"
    assert out["fallback_used"] is True
    assert out["fallback_reason"] == "gpu_unhealthy"
    assert out["content"] == "fallback-ok"
    assert after == before + 1


def test_ps54_gpu_success_path_has_no_fallback(monkeypatch):
    monkeypatch.setattr("config.settings.llm_backend", "gpu")
    monkeypatch.setattr("apps.llm_gateway.can_use_gpu_backend", lambda: (True, ""))
    monkeypatch.setattr("apps.llm_gateway.mark_gpu_backend_success", lambda: None)
    monkeypatch.setattr(
        "apps.llm_gateway.get_backend_generator",
        lambda backend: (
            lambda **_: {
                "backend_actual": "gpu",
                "content": "ok",
                "usage": {"total_tokens": 4},
                "model_id": "qwen/qwen2.5-0.5b-instruct",
                "latency_ms": 12,
                "estimated_cost_usd": 0.0,
            }
        ),
    )
    out = generate(prompt="hi", node="decide", model_id="ignored")
    assert out["backend_requested"] == "gpu"
    assert out["backend_actual"] == "gpu"
    assert out["fallback_used"] is False
    assert out["fallback_reason"] == ""


def test_ps54_half_open_recovery_after_reset(monkeypatch):
    resilience.reset_gpu_resilience_state_for_tests()
    monkeypatch.setattr("config.settings.llm_gpu_circuit_breaker_failures", 1)
    monkeypatch.setattr("config.settings.llm_gpu_circuit_breaker_reset_seconds", 0.01)
    monkeypatch.setattr("config.settings.llm_gpu_healthcheck_timeout_seconds", 1.0)
    monkeypatch.setattr(
        "apps.llm_backends.resilience.check_nim_health", lambda timeout_s=0: False
    )

    allowed_1, reason_1 = resilience.can_use_gpu_backend()
    assert not allowed_1
    assert reason_1 == "gpu_unhealthy"

    allowed_2, reason_2 = resilience.can_use_gpu_backend()
    assert not allowed_2
    assert reason_2 == "gpu_circuit_open"

    state = resilience._state_for(resilience.GPU_CIRCUIT_KEY)  # type: ignore[attr-defined]
    state.last_failure_monotonic_s -= 1.0
    monkeypatch.setattr(
        "apps.llm_backends.resilience.check_nim_health", lambda timeout_s=0: True
    )

    allowed_3, reason_3 = resilience.can_use_gpu_backend()
    assert allowed_3
    assert reason_3 == ""


def test_ps54_budget_exceeded_on_gpu_does_not_fallback(monkeypatch):
    monkeypatch.setattr("config.settings.llm_backend", "gpu")
    monkeypatch.setattr("apps.llm_gateway.can_use_gpu_backend", lambda: (True, ""))
    monkeypatch.setattr(
        "apps.llm_gateway.get_backend_generator",
        lambda backend: (
            (lambda **_: (_ for _ in ()).throw(LLMBudgetExceededError("budget")))
            if backend == "gpu"
            else (
                lambda **_: (_ for _ in ()).throw(
                    AssertionError("openai fallback used")
                )
            )
        ),
    )
    try:
        generate(prompt="hi", node="decide")
        raise AssertionError("Expected LLMBudgetExceededError")
    except LLMBudgetExceededError:
        pass


def test_ps54_budget_exceeded_on_openai_does_not_retry_other_backend(monkeypatch):
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr("config.settings.openai_api_key", "test-openai-key")
    monkeypatch.setattr(
        "apps.llm_gateway.get_backend_generator",
        lambda backend: (
            (lambda **_: (_ for _ in ()).throw(LLMBudgetExceededError("budget")))
            if backend == "openai"
            else (
                lambda **_: (_ for _ in ()).throw(
                    AssertionError("cross-backend retry used")
                )
            )
        ),
    )

    with pytest.raises(LLMBudgetExceededError):
        generate(prompt="hi", node="decide")


@pytest.mark.parametrize(
    ("exc_type", "fallback_reason"),
    [
        (LLMGatewayTimeoutError, "gpu_timeout"),
        (LLMGatewayProviderError, "gpu_error"),
    ],
)
def test_ps54_gpu_runtime_failure_fallbacks_and_marks_failure(
    monkeypatch, exc_type, fallback_reason
):
    failures: list[None] = []
    monkeypatch.setattr("config.settings.llm_backend", "gpu")
    monkeypatch.setattr("config.settings.openai_api_key", "test-openai-key")
    monkeypatch.setattr("apps.llm_gateway.can_use_gpu_backend", lambda: (True, ""))
    monkeypatch.setattr(
        "apps.llm_gateway.mark_gpu_backend_failure", lambda: failures.append(None)
    )
    monkeypatch.setattr(
        "apps.llm_gateway.get_backend_generator",
        lambda backend: (
            (lambda **_: (_ for _ in ()).throw(exc_type("gpu failed")))
            if backend == "gpu"
            else (
                lambda **_: {
                    "backend_actual": "openai",
                    "content": "fallback-ok",
                    "usage": {"total_tokens": 1},
                    "model_id": "gpt-4o-mini",
                    "latency_ms": 3,
                    "estimated_cost_usd": 0.0,
                }
            )
        ),
    )

    before = _counter_value(
        from_backend="gpu", to_backend="openai", reason=fallback_reason
    )
    out = generate(prompt="hi", node="decide", model_id="gpt-4o-mini")
    after = _counter_value(
        from_backend="gpu", to_backend="openai", reason=fallback_reason
    )

    assert failures == [None]
    assert out["backend_requested"] == "gpu"
    assert out["backend_actual"] == "openai"
    assert out["fallback_used"] is True
    assert out["fallback_reason"] == fallback_reason
    assert out["content"] == "fallback-ok"
    assert after == before + 1


def test_ps54_no_openai_key_on_gpu_failure_raises_provider_error(monkeypatch):
    monkeypatch.setattr("config.settings.llm_backend", "gpu")
    monkeypatch.setattr("config.settings.openai_api_key", "")
    monkeypatch.setattr(
        "apps.llm_gateway.can_use_gpu_backend", lambda: (False, "gpu_circuit_open")
    )
    monkeypatch.setattr(
        "apps.llm_gateway.get_backend_generator",
        lambda backend: (lambda **_: {"backend_actual": backend}),
    )
    try:
        generate(prompt="hi", node="decide")
        raise AssertionError("Expected LLMGatewayProviderError")
    except LLMGatewayProviderError:
        pass
