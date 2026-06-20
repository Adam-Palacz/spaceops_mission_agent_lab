"""PS7.6 — Postgres LLM budget mode tests."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from apps.llm_cost import (
    enforce_budget_before_generate,
    get_budget_snapshot_for_tests,
    reset_llm_cost_state_for_tests,
)
from apps.llm_gateway import generate
from apps.llm_gateway_errors import LLMBudgetExceededError

REPO_ROOT = Path(__file__).resolve().parents[1]
CHART = REPO_ROOT / "deploy" / "helm" / "spaceops"
PS76 = (
    REPO_ROOT
    / "roadmap"
    / "02-production-scale"
    / "sprint-7"
    / "PS7.6-postgres-llm-budget-mode.md"
)
MIGRATION = (
    REPO_ROOT / "alembic" / "versions" / "20260603_0003_ps76_llm_usage_ledger.py"
)
SQL = REPO_ROOT / "infra" / "sql" / "002_llm_usage_ledger.sql"


@pytest.fixture(autouse=True)
def _reset_llm_cost_state():
    reset_llm_cost_state_for_tests()
    yield
    reset_llm_cost_state_for_tests()


def test_ps76_deliverables_exist() -> None:
    assert PS76.is_file()
    assert MIGRATION.is_file()
    assert SQL.is_file()
    text = PS76.read_text(encoding="utf-8")
    assert "| **Status** | Done |" in text


def test_ps76_postgres_mode_shared_cap_blocks_next_call(monkeypatch):
    ledger_used = {"tokens": 0}

    def _get_daily_tokens_used(**_kwargs):
        return ledger_used["tokens"]

    def _add_daily_tokens(*, tokens: int, **_kwargs):
        ledger_used["tokens"] += max(0, int(tokens or 0))
        return ledger_used["tokens"]

    monkeypatch.setattr("config.settings.llm_budget_mode", "postgres")
    monkeypatch.setattr("config.settings.llm_daily_token_budget", 5)
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    monkeypatch.setattr("config.settings.llm_backend", "openai")
    monkeypatch.setattr(
        "apps.llm_usage_ledger.get_daily_tokens_used", _get_daily_tokens_used
    )
    monkeypatch.setattr("apps.llm_usage_ledger.add_daily_tokens", _add_daily_tokens)
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
    assert snap.mode == "postgres"
    assert snap.postgres_tokens_used == 6
    with pytest.raises(LLMBudgetExceededError, match="postgres mode"):
        generate(prompt="c", node="report")


def test_ps76_postgres_enforce_reads_ledger_before_generate(monkeypatch):
    monkeypatch.setattr("config.settings.llm_budget_mode", "postgres")
    monkeypatch.setattr("config.settings.llm_daily_token_budget", 10)
    monkeypatch.setattr("apps.llm_usage_ledger.get_daily_tokens_used", lambda **_k: 10)

    with pytest.raises(LLMBudgetExceededError, match="postgres mode"):
        enforce_budget_before_generate(node="triage")


def test_ps76_postgres_mode_disabled_when_budget_zero(monkeypatch):
    monkeypatch.setattr("config.settings.llm_budget_mode", "postgres")
    monkeypatch.setattr("config.settings.llm_daily_token_budget", 0)
    monkeypatch.setattr("config.settings.openai_api_key", "test-key")
    monkeypatch.setattr("config.settings.llm_backend", "openai")
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


def _helm_available() -> bool:
    return shutil.which("helm") is not None


def _helm_template(name: str, value_files: list[str]) -> str:
    cmd = ["helm", "template", name, str(CHART)]
    for vf in value_files:
        cmd.extend(["-f", str(CHART / vf)])
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
@pytest.mark.parametrize(
    ("release", "values_file", "budget_mode", "token_budget"),
    [
        ("spaceops-stage-ps76", "values-stage.yaml", "postgres", "250000"),
        ("spaceops-prod-ps76", "values-prod.yaml", "postgres", "500000"),
    ],
)
def test_ps76_stage_prod_helm_wires_postgres_budget(
    release: str, values_file: str, budget_mode: str, token_budget: str
) -> None:
    out = _helm_template(release, ["values.yaml", values_file])
    assert re.search(rf'name: LLM_BUDGET_MODE\s*\n\s*value: "{budget_mode}"', out)
    assert re.search(
        rf'name: LLM_DAILY_TOKEN_BUDGET\s*\n\s*value: "{token_budget}"', out
    )
    assert "name: LLM_BUDGET_SOFT_WARNING_RATIO" in out
