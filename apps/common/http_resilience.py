"""
S3.4 — Retry with exponential backoff and circuit breaker for HTTP/MCP calls.

Provides sync and async helpers. When the circuit is open, calls fail fast (fail-closed).
Logs retries and circuit state changes.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any, Callable, TypeVar

from config import settings

_T = TypeVar("_T")
_Logger = logging.getLogger(__name__)

# Per-key circuit state: (failure_count, last_failure_time, state)
# state: "closed" | "open" | "half_open"
_circuit: dict[str, tuple[int, float, str]] = {}


def _get_circuit(key: str) -> tuple[int, float, str]:
    reset_s = max(
        0.0, getattr(settings, "http_resilience_circuit_breaker_reset_seconds", 60.0)
    )
    if key not in _circuit:
        _circuit[key] = (0, 0.0, "closed")
    count, last_time, state = _circuit[key]
    now = time.monotonic()
    if state == "open" and (now - last_time) >= reset_s:
        _circuit[key] = (0, last_time, "half_open")
        return (0, last_time, "half_open")
    return (count, last_time, state)


def _record_success(key: str) -> None:
    if key in _circuit:
        _circuit[key] = (0, _circuit[key][1], "closed")


def _record_failure(key: str) -> None:
    max_f = max(0, getattr(settings, "http_resilience_circuit_breaker_failures", 5))
    if max_f == 0:
        return
    now = time.monotonic()
    if key not in _circuit:
        _circuit[key] = (0, 0.0, "closed")
    count, _, state = _circuit[key]
    count += 1
    if count >= max_f:
        _circuit[key] = (count, now, "open")
        _Logger.warning(
            "http_resilience: circuit open for key=%s after %d failures", key, count
        )
    else:
        _circuit[key] = (count, now, state)


class CircuitOpenError(Exception):
    """Raised when the circuit breaker is open for the given key."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Circuit open for key={key}")


def reset_circuit(key: str | None = None) -> None:
    """Reset circuit state for a key or all keys (for tests)."""
    global _circuit
    if key is None:
        _circuit.clear()
    elif key in _circuit:
        del _circuit[key]


def _is_retryable(exc: BaseException) -> bool:
    """Treat timeouts, connection errors, and 5xx as retryable."""
    import httpx

    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = getattr(exc, "response", None)
        if code is not None:
            status = getattr(code, "status_code", 0)
            return status >= 500 or status == 429
    return False


def with_retry_sync(
    fn: Callable[..., _T],
    *args: Any,
    circuit_key: str | None = None,
    **kwargs: Any,
) -> _T:
    """
    Run fn(*args, **kwargs) with retries and optional circuit breaker.

    Uses config: http_resilience_max_retries, http_resilience_backoff_base_seconds,
    http_resilience_circuit_breaker_failures, http_resilience_circuit_breaker_reset_seconds.
    """
    max_retries = max(0, getattr(settings, "http_resilience_max_retries", 3))
    backoff_base = max(
        0.0, getattr(settings, "http_resilience_backoff_base_seconds", 1.0)
    )
    max_f = getattr(settings, "http_resilience_circuit_breaker_failures", 5)
    last_exc: BaseException | None = None

    for attempt in range(max_retries + 1):
        if circuit_key and max_f > 0:
            count, last_time, state = _get_circuit(circuit_key)
            if state == "open":
                raise CircuitOpenError(circuit_key)

        try:
            result = fn(*args, **kwargs)
            if circuit_key:
                _record_success(circuit_key)
            return result
        except BaseException as e:
            last_exc = e
            if circuit_key:
                _record_failure(circuit_key)
            if circuit_key and max_f > 0:
                _, _, state = _get_circuit(circuit_key)
                if state == "open":
                    raise CircuitOpenError(circuit_key) from e
            if not _is_retryable(e) or attempt >= max_retries:
                raise
            delay = backoff_base * (2**attempt) * (0.5 + 0.5 * random.random())
            _Logger.info(
                "http_resilience: retry attempt %s after %s: %s",
                attempt + 1,
                type(e).__name__,
                circuit_key or "n/a",
            )
            time.sleep(delay)

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("with_retry_sync: unreachable")


async def with_retry_async(
    async_fn: Callable[..., Any],
    *args: Any,
    circuit_key: str | None = None,
    **kwargs: Any,
) -> Any:
    """
    Await async_fn(*args, **kwargs) with retries and optional circuit breaker.

    Same config as with_retry_sync. Use for MCP/async HTTP calls.
    """
    max_retries = max(0, getattr(settings, "http_resilience_max_retries", 3))
    backoff_base = max(
        0.0, getattr(settings, "http_resilience_backoff_base_seconds", 1.0)
    )
    max_f = getattr(settings, "http_resilience_circuit_breaker_failures", 5)
    last_exc: BaseException | None = None

    for attempt in range(max_retries + 1):
        if circuit_key and max_f > 0:
            count, last_time, state = _get_circuit(circuit_key)
            if state == "open":
                raise CircuitOpenError(circuit_key)

        try:
            result = await async_fn(*args, **kwargs)
            if circuit_key:
                _record_success(circuit_key)
            return result
        except BaseException as e:
            last_exc = e
            if circuit_key:
                _record_failure(circuit_key)
            if circuit_key and max_f > 0:
                _, _, state = _get_circuit(circuit_key)
                if state == "open":
                    raise CircuitOpenError(circuit_key) from e
            if not _is_retryable(e) or attempt >= max_retries:
                raise
            delay = backoff_base * (2**attempt) * (0.5 + 0.5 * random.random())
            _Logger.info(
                "http_resilience: retry attempt %s after %s: %s",
                attempt + 1,
                type(e).__name__,
                circuit_key or "n/a",
            )
            await asyncio.sleep(delay)

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("with_retry_async: unreachable")
