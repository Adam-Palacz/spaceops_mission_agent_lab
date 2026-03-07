"""
S3.4 — Tests for HTTP/MCP retry and circuit breaker.

Covers: retries on transient errors, circuit opening after repeated failures,
short-circuit when open, and (optional) recovery when service comes back.
"""

from __future__ import annotations

from unittest.mock import patch
import httpx
import pytest

from apps.common.http_resilience import (
    CircuitOpenError,
    reset_circuit,
    with_retry_async,
    with_retry_sync,
)


@pytest.fixture(autouse=True)
def _reset_circuits():
    """Isolate tests by clearing circuit state."""
    reset_circuit()
    yield
    reset_circuit()


@patch("apps.common.http_resilience.settings")
def test_retry_sync_succeeds_after_transient_failures(mock_settings):
    """Retries on transient errors and returns on first success."""
    mock_settings.http_resilience_max_retries = 3
    mock_settings.http_resilience_backoff_base_seconds = 0.01
    mock_settings.http_resilience_circuit_breaker_failures = 0  # disabled

    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise httpx.TimeoutException("timeout")
        return 42

    result = with_retry_sync(flaky)
    assert result == 42
    assert len(calls) == 3


@patch("apps.common.http_resilience.settings")
def test_retry_sync_raises_after_max_retries(mock_settings):
    """After max retries, last exception is raised."""
    mock_settings.http_resilience_max_retries = 2
    mock_settings.http_resilience_backoff_base_seconds = 0.01
    mock_settings.http_resilience_circuit_breaker_failures = 0

    def always_fail():
        raise httpx.ConnectError("unreachable")

    with pytest.raises(httpx.ConnectError):
        with_retry_sync(always_fail)


@patch("apps.common.http_resilience.settings")
def test_circuit_breaker_opens_and_short_circuits(mock_settings):
    """After N failures, circuit opens and next call raises CircuitOpenError."""
    mock_settings.http_resilience_max_retries = 2
    mock_settings.http_resilience_backoff_base_seconds = 0.01
    mock_settings.http_resilience_circuit_breaker_failures = 3
    mock_settings.http_resilience_circuit_breaker_reset_seconds = 60.0

    def fail():
        raise httpx.TimeoutException("timeout")

    # First call: 3 attempts (max_retries=2), all fail → circuit opens → CircuitOpenError
    with pytest.raises(CircuitOpenError) as exc_info:
        with_retry_sync(fail, circuit_key="test_circuit")
    assert exc_info.value.key == "test_circuit"

    # Next call hits open circuit immediately (no attempt)
    with pytest.raises(CircuitOpenError) as exc_info2:
        with_retry_sync(fail, circuit_key="test_circuit")
    assert exc_info2.value.key == "test_circuit"


@patch("apps.common.http_resilience.settings")
@pytest.mark.asyncio
async def test_retry_async_succeeds_after_transient_failures(mock_settings):
    """Async retry succeeds after transient failures."""
    mock_settings.http_resilience_max_retries = 3
    mock_settings.http_resilience_backoff_base_seconds = 0.01
    mock_settings.http_resilience_circuit_breaker_failures = 0

    calls = []

    async def flaky():
        calls.append(1)
        if len(calls) < 2:
            raise httpx.TimeoutException("timeout")
        return "ok"

    result = await with_retry_async(flaky)
    assert result == "ok"
    assert len(calls) == 2


@patch("apps.common.http_resilience.settings")
def test_opa_fail_closed_on_circuit_open(mock_settings):
    """When circuit is open, opa_allow returns False (fail-closed)."""
    from apps.agent.opa_client import opa_allow

    reset_circuit("opa")
    mock_settings.http_resilience_max_retries = 1
    mock_settings.http_resilience_backoff_base_seconds = 0.01
    mock_settings.http_resilience_circuit_breaker_failures = 2
    mock_settings.http_resilience_circuit_breaker_reset_seconds = 60.0

    with patch("apps.agent.opa_client.httpx.Client") as client_mock:
        client_mock.return_value.__enter__.return_value.post.side_effect = (
            httpx.TimeoutException("timeout")
        )
        # First call: retries then 2 failures recorded → circuit opens
        assert opa_allow({"action_type": "change_config", "action": "x"}, "i1") is False
        # Second call: circuit open → fail closed (False) without calling OPA
        assert opa_allow({"action_type": "change_config", "action": "x"}, "i1") is False
