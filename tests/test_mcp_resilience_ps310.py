"""
PS3.10 — MCP lossy-link resilience tests (CI-safe, no live OpenAI/MCP servers).
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import httpx
import pytest

from apps.agent.nodes import check_escalation, investigate
from apps.common.http_resilience import (
    CircuitOpenError,
    reset_circuit,
    with_retry_async,
)


def test_ps310_mcp_key_matrix_uses_distinct_circuit_keys(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Ensure telemetry and KB tools use separate circuit keys:
    - mcp_telemetry
    - mcp_kb_runbooks
    - mcp_kb_postmortems
    """
    from apps.agent import mcp_client

    seen: list[str] = []

    async def _fake_with_retry_async(async_fn, *args, circuit_key=None, **kwargs):
        seen.append(str(circuit_key or ""))
        raise CircuitOpenError(str(circuit_key or ""))

    monkeypatch.setattr(mcp_client, "_MCP_AVAILABLE", True)
    monkeypatch.setattr(mcp_client, "with_retry_async", _fake_with_retry_async)

    assert (
        asyncio.run(
            mcp_client._call_telemetry_mcp(
                "2025-02-14T09:00:00Z", "2025-02-14T11:00:00Z"
            )
        )
        == []
    )
    assert asyncio.run(mcp_client._call_kb_runbooks_mcp("power", 5)) == []
    assert asyncio.run(mcp_client._call_kb_postmortems_mcp("power", 5)) == []

    assert seen == ["mcp_telemetry", "mcp_kb_runbooks", "mcp_kb_postmortems"]


def test_ps310_investigate_tool_failures_escalate_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Lossy links / tool outages should produce tool_failure outcomes and escalation.
    """

    def _conn_err(*_args, **_kwargs):
        raise httpx.ConnectError("mcp down")

    monkeypatch.setattr("apps.agent.nodes.call_telemetry", _conn_err)
    monkeypatch.setattr("apps.agent.nodes.call_search_runbooks", _conn_err)
    monkeypatch.setattr("apps.agent.nodes.call_search_postmortems", _conn_err)

    state = {
        "incident_id": "ps310-inc",
        "trace_id": "ps310-inc",
        "payload": {
            "time_range_start": "2025-02-14T09:00:00Z",
            "time_range_end": "2025-02-14T11:00:00Z",
        },
        "subsystem": "Power",
        "risk": "high",
    }
    out = investigate(state)
    assert out["tool_outcomes"]["query_telemetry"] == "failure"
    assert out["tool_outcomes"]["search_runbooks"] == "failure"
    assert out["tool_outcomes"]["search_postmortems"] == "failure"

    esc = check_escalation({**state, **out})
    assert esc.get("escalated") is True
    assert (esc.get("escalation_packet") or {}).get("reason") == "tool_failure"


@pytest.mark.asyncio
async def test_ps310_421_status_is_retryable(monkeypatch: pytest.MonkeyPatch):
    """
    421-class MCP transport errors should retry and eventually succeed.
    """
    attempts = {"n": 0}

    class _Resp:
        status_code = 421

    async def _flaky():
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise httpx.HTTPStatusError("421", request=MagicMock(), response=_Resp())
        return "ok"

    monkeypatch.setattr("config.settings.http_resilience_max_retries", 2)
    monkeypatch.setattr("config.settings.http_resilience_backoff_base_seconds", 0.0)
    monkeypatch.setattr("config.settings.http_resilience_circuit_breaker_failures", 0)
    out = await with_retry_async(_flaky, circuit_key="mcp_telemetry")
    assert out == "ok"
    assert attempts["n"] == 2


@pytest.mark.asyncio
async def test_ps310_open_circuit_fails_fast_without_spin(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Once open, same key should short-circuit immediately on next call.
    """
    reset_circuit("mcp_telemetry")
    monkeypatch.setattr("config.settings.http_resilience_max_retries", 1)
    monkeypatch.setattr("config.settings.http_resilience_backoff_base_seconds", 0.0)
    monkeypatch.setattr("config.settings.http_resilience_circuit_breaker_failures", 2)
    monkeypatch.setattr(
        "config.settings.http_resilience_circuit_breaker_reset_seconds", 9999.0
    )

    calls = {"n": 0}

    async def _always_timeout():
        calls["n"] += 1
        raise httpx.TimeoutException("timeout")

    with pytest.raises(CircuitOpenError):
        await with_retry_async(_always_timeout, circuit_key="mcp_telemetry")
    first_calls = calls["n"]
    assert first_calls >= 1

    with pytest.raises(CircuitOpenError):
        await with_retry_async(_always_timeout, circuit_key="mcp_telemetry")
    # No extra underlying attempt when already open.
    assert calls["n"] == first_calls
