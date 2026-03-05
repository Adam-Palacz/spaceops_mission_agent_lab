"""
S2.4 / S2.10 — OPA client and fail-closed behaviour.

Tests: opa_allow() returns True only when OPA returns allow; on timeout/error/malformed → False.
Optional: policy behaviour (allowlist, "restart all" deny) when OPA server is reachable.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import os

import httpx
import pytest

from apps.agent.opa_client import opa_allow


def test_opa_allow_returns_true_when_opa_returns_allow():
    """S2.4/S2.10: OPA returns result: true → opa_allow returns True."""
    with patch("apps.agent.opa_client.httpx.Client") as m:
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = lambda: None
        resp.json.return_value = {"result": True}
        m.return_value.__enter__.return_value.post.return_value = resp
        assert (
            opa_allow(
                {"action_type": "change_config", "action": "Adjust threshold"}, "inc-1"
            )
            is True
        )


def test_opa_allow_returns_false_when_opa_returns_deny():
    """S2.4/S2.10: OPA returns result: false → opa_allow returns False."""
    with patch("apps.agent.opa_client.httpx.Client") as m:
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = lambda: None
        resp.json.return_value = {"result": False}
        m.return_value.__enter__.return_value.post.return_value = resp
        assert (
            opa_allow(
                {"action_type": "change_config", "action": "restart all systems"},
                "inc-1",
            )
            is False
        )


def test_opa_allow_fail_closed_on_timeout():
    """S2.4/S2.10: On OPA timeout → deny (fail-closed)."""
    with patch("apps.agent.opa_client.httpx.Client") as m:
        m.return_value.__enter__.return_value.post.side_effect = httpx.TimeoutException(
            "timeout"
        )
        assert (
            opa_allow({"action_type": "change_config", "action": "test"}, "inc-1")
            is False
        )


def test_opa_allow_fail_closed_on_connection_error():
    """S2.4/S2.10: When OPA is down (connection error) → deny."""
    with patch("apps.agent.opa_client.httpx.Client") as m:
        m.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError(
            "unreachable"
        )
        assert (
            opa_allow({"action_type": "restart_service", "action": "test"}, "inc-1")
            is False
        )


def test_opa_allow_fail_closed_on_http_500():
    """S2.4/S2.10: OPA returns 5xx → deny."""
    with patch("apps.agent.opa_client.httpx.Client") as m:
        resp = MagicMock()
        resp.status_code = 500

        def do_raise():
            raise httpx.HTTPStatusError("500", request=MagicMock(), response=resp)

        resp.raise_for_status = do_raise
        m.return_value.__enter__.return_value.post.return_value = resp
        assert (
            opa_allow({"action_type": "change_config", "action": "test"}, "inc-1")
            is False
        )


def test_opa_allow_fail_closed_on_malformed_response():
    """S2.4/S2.10: Malformed or unexpected OPA response → deny."""
    with patch("apps.agent.opa_client.httpx.Client") as m:
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = lambda: None
        resp.json.return_value = {"result": "not-a-bool"}
        m.return_value.__enter__.return_value.post.return_value = resp
        assert (
            opa_allow({"action_type": "change_config", "action": "test"}, "inc-1")
            is False
        )


def test_opa_allow_fail_closed_on_empty_result():
    """S2.4/S2.10: OPA response with no result key → deny."""
    with patch("apps.agent.opa_client.httpx.Client") as m:
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = lambda: None
        resp.json.return_value = {}
        m.return_value.__enter__.return_value.post.return_value = resp
        assert (
            opa_allow({"action_type": "change_config", "action": "test"}, "inc-1")
            is False
        )


@pytest.mark.skipif(
    not os.getenv("OPA_POLICY_INTEGRATION"),
    reason="Integration: requires OPA server on OPA_URL (e.g. docker compose -f infra/docker-compose.yml up -d opa) and OPA_POLICY_INTEGRATION=1",
)
def test_opa_policy_allowlist_and_restart_all_deny_integration():
    """S2.10: With real OPA, allowlisted tool + valid args → allow; 'restart all' in action → deny."""
    # Allowed: change_config, valid action text
    assert (
        opa_allow(
            {
                "action_type": "change_config",
                "action": "Increase heater setpoint on unit A",
            },
            "inc-int",
        )
        is True
    )
    # Denied: "restart all" in action text
    assert (
        opa_allow(
            {"action_type": "change_config", "action": "Restart all services now"},
            "inc-int",
        )
        is False
    )
    # Denied: action_type not in allowlist
    assert (
        opa_allow(
            {"action_type": "unknown_tool", "action": "Do something"},
            "inc-int",
        )
        is False
    )
