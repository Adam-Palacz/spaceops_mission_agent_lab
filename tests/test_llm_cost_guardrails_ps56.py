from __future__ import annotations

import pytest

from apps.llm_cost import (
    LLM_ESTIMATED_COST_USD_TOTAL,
    LLM_TOKENS_TOTAL,
    get_budget_snapshot_for_tests,
    reset_llm_cost_state_for_tests,
)
from apps.llm_gateway import generate
from apps.llm_gateway_errors import LLMBudgetExceededError


@pytest.fixture(autouse=True)
def _reset_llm_cost_state():
    reset_llm_cost_state_for_tests()
    yield
    reset_llm_cost_state_for_tests()


def test_ps56_process_mode_counter_increments_and_hard_cap_blocks_next_call(
    monkeypatch,
):
    monkeypatch.setattr("config.settings.llm_budget_mode", "process")
    monkeypatch.setattr("config.settings.llm_daily_token_budget", 5)
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr(
        "apps.llm_gateway.get_backend_generator",
        lambda backend: (
            lambda **_: {
                "backend_actual": backend,
                "content": "ok",
                "usage": {"total_tokens": 3},
                "model_id": "gpt-4o-mini",
                "latency_ms": 1,
                "estimated_cost_usd": 0.0,
            }
        ),
    )

    generate(prompt="a", node="triage")
    generate(prompt="b", node="decide")
    snap = get_budget_snapshot_for_tests()
    assert snap.mode == "process"
    assert snap.process_tokens_used == 6
    with pytest.raises(LLMBudgetExceededError):
        generate(prompt="c", node="report")


def test_ps56_process_mode_new_process_reset_semantics(monkeypatch):
    monkeypatch.setattr("config.settings.llm_budget_mode", "process")
    monkeypatch.setattr("config.settings.llm_daily_token_budget", 2)
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr(
        "apps.llm_gateway.get_backend_generator",
        lambda backend: (
            lambda **_: {
                "backend_actual": backend,
                "content": "ok",
                "usage": {"total_tokens": 2},
                "model_id": "gpt-4o-mini",
                "latency_ms": 1,
                "estimated_cost_usd": 0.0,
            }
        ),
    )

    generate(prompt="x", node="triage")
    with pytest.raises(LLMBudgetExceededError):
        generate(prompt="y", node="triage")

    # Simulate process restart semantics: in-memory counter resets.
    reset_llm_cost_state_for_tests()
    generate(prompt="z", node="triage")
    assert get_budget_snapshot_for_tests().process_tokens_used == 2


def test_ps56_records_token_and_estimated_cost_metrics(monkeypatch):
    monkeypatch.setattr("config.settings.llm_budget_mode", "process")
    monkeypatch.setattr("config.settings.llm_daily_token_budget", 0)
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr(
        "apps.llm_gateway.get_backend_generator",
        lambda backend: (
            lambda **_: {
                "backend_actual": backend,
                "content": "ok",
                "usage": {"total_tokens": 7},
                "model_id": "gpt-4o-mini",
                "latency_ms": 1,
                "estimated_cost_usd": 0.03,
            }
        ),
    )

    token_metric = LLM_TOKENS_TOTAL.labels(
        backend_actual="openai", model_id="gpt-4o-mini", node="cost_metric_test"
    )
    cost_metric = LLM_ESTIMATED_COST_USD_TOTAL.labels(
        backend_actual="openai", model_id="gpt-4o-mini", node="cost_metric_test"
    )
    tokens_before = float(token_metric._value.get())  # type: ignore[attr-defined]
    cost_before = float(cost_metric._value.get())  # type: ignore[attr-defined]

    generate(prompt="metric", node="cost_metric_test")

    assert float(token_metric._value.get()) == tokens_before + 7  # type: ignore[attr-defined]
    assert float(cost_metric._value.get()) == cost_before + 0.03  # type: ignore[attr-defined]


def test_ps56_gpu_budget_exceeded_raises_without_fallback(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr("config.settings.llm_budget_mode", "process")
    monkeypatch.setattr("config.settings.llm_daily_token_budget", 1)
    monkeypatch.setattr("config.settings.llm_backend", "gpu")
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    monkeypatch.setattr("apps.llm_gateway.can_use_gpu_backend", lambda: (True, ""))
    monkeypatch.setattr("apps.llm_gateway.mark_gpu_backend_success", lambda: None)
    monkeypatch.setattr(
        "apps.llm_gateway.get_backend_generator",
        lambda backend: (
            lambda **_: (
                calls.append(backend)
                or {
                    "backend_actual": backend,
                    "content": "ok",
                    "usage": {"total_tokens": 1},
                    "model_id": "qwen/qwen2.5-0.5b-instruct",
                    "latency_ms": 1,
                    "estimated_cost_usd": 0.0,
                }
            )
        ),
    )
    generate(prompt="first", node="decide")
    with pytest.raises(LLMBudgetExceededError):
        generate(prompt="second", node="decide")

    assert calls == ["gpu"]  # no openai fallback call on budget deny


def test_ps56_openai_budget_exceeded_does_not_attempt_gpu(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr("config.settings.llm_budget_mode", "process")
    monkeypatch.setattr("config.settings.llm_daily_token_budget", 1)
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    monkeypatch.setattr(
        "apps.llm_gateway.get_backend_generator",
        lambda backend: (
            lambda **_: (
                calls.append(backend)
                or {
                    "backend_actual": backend,
                    "content": "ok",
                    "usage": {"total_tokens": 1},
                    "model_id": "gpt-4o-mini",
                    "latency_ms": 1,
                    "estimated_cost_usd": 0.0,
                }
            )
        ),
    )
    generate(prompt="first", node="decide")
    with pytest.raises(LLMBudgetExceededError):
        generate(prompt="second", node="decide")

    assert calls == ["openai"]


def test_ps56_postgres_mode_requires_positive_budget_to_enforce(monkeypatch):
    monkeypatch.setattr("config.settings.llm_budget_mode", "postgres")
    monkeypatch.setattr("config.settings.llm_daily_token_budget", 10)
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    monkeypatch.setattr("apps.llm_usage_ledger.get_daily_tokens_used", lambda **_k: 10)
    with pytest.raises(LLMBudgetExceededError, match="postgres mode"):
        generate(prompt="x", node="triage")


def test_ps56_postgres_mode_with_zero_budget_allows_calls(monkeypatch):
    monkeypatch.setattr("config.settings.llm_budget_mode", "postgres")
    monkeypatch.setattr("config.settings.llm_daily_token_budget", 0)
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    monkeypatch.setattr("apps.llm_usage_ledger.get_daily_tokens_used", lambda **_k: 999)
    monkeypatch.setattr("apps.llm_usage_ledger.add_daily_tokens", lambda **_k: 999)
    monkeypatch.setattr(
        "apps.llm_gateway.get_backend_generator",
        lambda backend: (
            lambda **_: {
                "backend_actual": backend,
                "content": "ok",
                "usage": {"total_tokens": 1},
                "model_id": "gpt-4o-mini",
                "latency_ms": 1,
                "estimated_cost_usd": 0.0,
            }
        ),
    )
    generate(prompt="x", node="triage")
