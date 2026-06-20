"""PS5.6 cost telemetry and honest budget guardrails (PS7.6 postgres mode)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from prometheus_client import Counter

from config import settings
from apps.llm_gateway_errors import LLMBudgetExceededError, LLMGatewayProviderError

_logger = logging.getLogger(__name__)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Total LLM tokens used by backend/model/node (PS5.6).",
    ["backend_actual", "model_id", "node"],
)

LLM_ESTIMATED_COST_USD_TOTAL = Counter(
    "llm_estimated_cost_usd_total",
    "Estimated LLM cost in USD by backend/model/node (PS5.6; estimate only).",
    ["backend_actual", "model_id", "node"],
)

_process_tokens_used = 0
_soft_warning_emitted = False


@dataclass(frozen=True)
class BudgetSnapshot:
    mode: str
    process_tokens_used: int
    postgres_tokens_used: int | None
    token_budget: int


def _budget_mode() -> str:
    raw = (getattr(settings, "llm_budget_mode", "process") or "process").strip().lower()
    if raw in ("", "process"):
        return "process"
    if raw == "postgres":
        return "postgres"
    raise LLMGatewayProviderError(
        f"Unsupported LLM_BUDGET_MODE='{raw}'. Supported: process|postgres."
    )


def _token_budget() -> int:
    return max(0, int(getattr(settings, "llm_daily_token_budget", 0) or 0))


def _soft_warning_threshold() -> int:
    budget = _token_budget()
    if budget <= 0:
        return 0
    ratio = float(getattr(settings, "llm_budget_soft_warning_ratio", 0.8) or 0.8)
    ratio = min(1.0, max(0.0, ratio))
    return int(budget * ratio)


def _maybe_emit_soft_warning(*, mode: str, used_tokens: int) -> None:
    global _soft_warning_emitted

    budget = _token_budget()
    if budget <= 0:
        return
    warn_at = _soft_warning_threshold()
    if warn_at > 0 and used_tokens >= warn_at and not _soft_warning_emitted:
        _soft_warning_emitted = True
        _logger.warning(
            "llm_budget_soft_warning mode=%s used_tokens=%d budget=%d",
            mode,
            used_tokens,
            budget,
        )


def enforce_budget_before_generate(*, node: str) -> None:
    """Raise LLMBudgetExceededError when current mode budget blocks new calls."""
    del node
    budget = _token_budget()
    if budget <= 0:
        return

    mode = _budget_mode()
    if mode == "process":
        if _process_tokens_used >= budget:
            raise LLMBudgetExceededError(
                "LLM token budget exceeded in process mode; set LLM_DAILY_TOKEN_BUDGET or restart process."
            )
        return

    from apps.llm_usage_ledger import get_daily_tokens_used

    used = get_daily_tokens_used()
    if used >= budget:
        raise LLMBudgetExceededError(
            "LLM token budget exceeded in postgres mode; shared daily org cap reached (UTC day)."
        )


def record_llm_usage(
    *,
    node: str,
    backend_actual: str,
    model_id: str,
    total_tokens: int,
    estimated_cost_usd: float,
) -> None:
    global _process_tokens_used

    tokens = max(0, int(total_tokens or 0))
    backend = (backend_actual or "unknown").strip()[:64] or "unknown"
    model = (model_id or "unknown").strip()[:128] or "unknown"
    node_label = (node or "unknown").strip()[:64] or "unknown"

    LLM_TOKENS_TOTAL.labels(
        backend_actual=backend, model_id=model, node=node_label
    ).inc(tokens)
    if estimated_cost_usd > 0:
        LLM_ESTIMATED_COST_USD_TOTAL.labels(
            backend_actual=backend, model_id=model, node=node_label
        ).inc(float(estimated_cost_usd))

    mode = _budget_mode()
    if mode == "process":
        _process_tokens_used += tokens
        _maybe_emit_soft_warning(mode="process", used_tokens=_process_tokens_used)
        return

    from apps.llm_usage_ledger import add_daily_tokens

    total = add_daily_tokens(tokens=tokens)
    _maybe_emit_soft_warning(mode="postgres", used_tokens=total)


def get_budget_snapshot_for_tests() -> BudgetSnapshot:
    mode = _budget_mode()
    postgres_used: int | None = None
    if mode == "postgres":
        from apps.llm_usage_ledger import get_daily_tokens_used

        postgres_used = get_daily_tokens_used()
    return BudgetSnapshot(
        mode=mode,
        process_tokens_used=_process_tokens_used,
        postgres_tokens_used=postgres_used,
        token_budget=_token_budget(),
    )


def reset_llm_cost_state_for_tests() -> None:
    global _process_tokens_used, _soft_warning_emitted
    _process_tokens_used = 0
    _soft_warning_emitted = False
