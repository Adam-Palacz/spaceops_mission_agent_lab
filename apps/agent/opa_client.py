"""
S2.3/S2.4 — OPA client for restricted-action policy.

S2.4: Call OPA /v1/data/agent/allow with input {incident_id, step}.
Fail-closed: on network error, timeout, non-200, or malformed response → deny.
"""

from __future__ import annotations

from typing import Any

import httpx

from config import settings


def _build_opa_input(step: dict, incident_id: str) -> dict:
    """Shape input for OPA policy."""
    return {
        "incident_id": incident_id,
        "step": step or {},
    }


def opa_allow(step: dict, incident_id: str) -> bool:
    """
    Check whether OPA allows the given restricted step.

    - Input: full plan step dict + incident_id.
    - Output: bool. Any error or unexpected shape → False (fail-closed, NF8).
    """
    url = getattr(
        settings,
        "opa_url",
        "http://localhost:8181/v1/data/agent/allow",
    )
    timeout = max(1, int(getattr(settings, "opa_timeout_seconds", 2)))
    payload = {"input": _build_opa_input(step, incident_id)}

    try:
        with httpx.Client(timeout=float(timeout)) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
    except Exception:
        # Fail-closed: unreachable / timeout / non-JSON → deny.
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
