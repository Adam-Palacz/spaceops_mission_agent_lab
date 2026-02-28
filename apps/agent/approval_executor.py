"""
S2.6 — Execute restricted action when an approval request is approved via API.

Runs only once per approval (caller ensures idempotent: only when status was pending).
Maps stored step (action_type) to MCP or no-op; writes outcome to audit via caller.
"""

from __future__ import annotations

from typing import Any


def execute_approved_action(approval_id: str, rec: dict[str, Any]) -> dict[str, Any]:
    """
    Execute the stored restricted action for an approved request.

    Call only when the request was just approved (status was pending).
    Returns {"outcome": "success"|"failure", "result": ...} or {"outcome": "failure", "error_message": ...}.
    """
    step = rec.get("step") or {}
    action_type = (step.get("action_type") or "").strip().lower()
    incident_id = rec.get("incident_id") or "unknown"
    action_text = (step.get("action") or "")[:500]

    if action_type == "change_config":
        return _execute_change_config(approval_id, incident_id, action_text)
    if action_type == "restart_service":
        return _execute_restart_service(approval_id, incident_id, action_text)
    return {
        "outcome": "failure",
        "error_message": f"Unknown action_type for execution: {action_type!r}",
    }


def _execute_change_config(
    approval_id: str, incident_id: str, action_text: str
) -> dict[str, Any]:
    """Execute change_config via GitOps create_pr (S2.2)."""
    from apps.agent.mcp_client import call_create_pr

    branch = f"agent/{incident_id}-approved-{approval_id[:8]}"
    files = [
        {
            "path": "alerts/approved-change.yaml",
            "content": f"# Approved config change (approval {approval_id})\n# {action_text}\n",
        }
    ]
    try:
        result = call_create_pr(repo_path=None, branch=branch, files=files)
        if result and result.get("pr_url"):
            return {"outcome": "success", "result": result}
        if result and result.get("push_error"):
            return {
                "outcome": "failure",
                "error_message": result.get("push_error", "Push/PR failed"),
                "result": result,
            }
        return {"outcome": "success", "result": result or {}}
    except Exception as e:
        return {"outcome": "failure", "error_message": str(e)[:200]}


def _execute_restart_service(
    approval_id: str, incident_id: str, action_text: str
) -> dict[str, Any]:
    """Restart requested: no MCP in MVP; audit only (no-op)."""
    return {
        "outcome": "success",
        "result": {
            "message": "restart_service requested (no-op in MVP)",
            "action": action_text[:100],
        },
    }
