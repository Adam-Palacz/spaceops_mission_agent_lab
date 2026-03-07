"""
S2.3/S2.4 — OPA client for restricted-action policy.

S2.4: Call OPA /v1/data/agent/allow with input {incident_id, step}.
Fail-closed: on network error, timeout, non-200, or malformed response → deny.
S3.4: Retry with backoff and circuit breaker; circuit open → deny.
"""

from __future__ import annotations

from typing import Any

import httpx

from config import settings
from apps.common.http_resilience import CircuitOpenError, with_retry_sync


def _build_opa_input(step: dict, incident_id: str) -> dict:
    """Shape input for OPA policy."""
    return {
        "incident_id": incident_id,
        "step": step or {},
    }


def _opa_post(url: str, timeout: float, payload: dict) -> dict[str, Any]:
    """Single OPA POST; used inside retry loop."""
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


def opa_allow(step: dict, incident_id: str) -> bool:
    """
    Check whether OPA allows the given restricted step.

    - Input: full plan step dict + incident_id.
    - Output: bool. Any error or unexpected shape → False (fail-closed, NF8).
    - S3.4: Retries on transient errors; circuit open → False.
    """
    url = getattr(
        settings,
        "opa_url",
        "http://localhost:8181/v1/data/agent/allow",
    )
    timeout = max(1, int(getattr(settings, "opa_timeout_seconds", 2)))
    payload = {"input": _build_opa_input(step, incident_id)}

    try:
        data = with_retry_sync(
            _opa_post,
            url,
            float(timeout),
            payload,
            circuit_key="opa",
        )
    except (CircuitOpenError, Exception):
        # Fail-closed: unreachable / timeout / circuit open / non-JSON → deny.
        return False

    # Fast path: result is a bare bool
    result = data.get("result")
    if isinstance(result, bool):
        return result
    if isinstance(result, dict):
        allow_value = result.get("allow")
        if isinstance(allow_value, bool):
            return allow_value
    # Unexpected shape → deny.
    return False
