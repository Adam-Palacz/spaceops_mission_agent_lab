"""PS5.4 GPU backend resilience: healthcheck + circuit breaker state."""

from __future__ import annotations

import time
from dataclasses import dataclass

from config import settings

from apps.llm_backends.nim_client import check_nim_health

GPU_CIRCUIT_KEY = "llm_gpu"


@dataclass
class _CircuitState:
    failures: int = 0
    last_failure_monotonic_s: float = 0.0
    state: str = "closed"  # closed | open | half_open
    health_checked: bool = False


_circuits: dict[str, _CircuitState] = {}


def _state_for(key: str) -> _CircuitState:
    if key not in _circuits:
        _circuits[key] = _CircuitState()
    return _circuits[key]


def _failure_threshold() -> int:
    return max(0, int(getattr(settings, "llm_gpu_circuit_breaker_failures", 3) or 0))


def _reset_window_seconds() -> float:
    return max(
        1.0,
        float(getattr(settings, "llm_gpu_circuit_breaker_reset_seconds", 60.0) or 60),
    )


def _health_timeout_seconds() -> float:
    return max(
        1.0, float(getattr(settings, "llm_gpu_healthcheck_timeout_seconds", 3.0) or 3)
    )


def _transition_open_to_half_open_if_due(state: _CircuitState) -> None:
    if state.state != "open":
        return
    elapsed = time.monotonic() - float(state.last_failure_monotonic_s or 0.0)
    if elapsed >= _reset_window_seconds():
        state.state = "half_open"
        state.health_checked = False


def mark_gpu_backend_success(*, key: str = GPU_CIRCUIT_KEY) -> None:
    state = _state_for(key)
    state.failures = 0
    state.state = "closed"
    state.health_checked = True


def mark_gpu_backend_failure(*, key: str = GPU_CIRCUIT_KEY) -> None:
    state = _state_for(key)
    state.failures += 1
    state.last_failure_monotonic_s = time.monotonic()
    threshold = _failure_threshold()
    if threshold > 0 and state.failures >= threshold:
        state.state = "open"


def can_use_gpu_backend(*, key: str = GPU_CIRCUIT_KEY) -> tuple[bool, str]:
    """
    Return (allowed, reason).

    Reasons:
      - "" when GPU is healthy and circuit permits calls
      - "gpu_circuit_open" when breaker is still open
      - "gpu_unhealthy" when healthcheck fails
    """
    state = _state_for(key)
    _transition_open_to_half_open_if_due(state)
    if state.state == "open":
        return False, "gpu_circuit_open"

    must_probe = (not state.health_checked) or state.state == "half_open"
    if must_probe:
        healthy = check_nim_health(timeout_s=_health_timeout_seconds())
        if not healthy:
            mark_gpu_backend_failure(key=key)
            return False, "gpu_unhealthy"
        state.health_checked = True
        if state.state == "half_open":
            state.failures = 0
            state.state = "closed"
    return True, ""


def reset_gpu_resilience_state_for_tests() -> None:
    _circuits.clear()
