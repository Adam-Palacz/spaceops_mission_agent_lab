"""
SpaceOps Agent — append-only audit log (S1.9, goals.md §4.6).
Schema: timestamp, trace_id, incident_id, actor, tool, args_hash, decision, policy_result, outcome, [error_message].
Storage: single NDJSON file; process only appends, no update/delete.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_AUDIT_PATH = REPO_ROOT / "data" / "audit.ndjson"


def _args_hash(args: dict) -> str:
    """Canonical hash of args for same args => same hash."""
    canonical = json.dumps(args, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_audit_path() -> Path:
    """Path to the audit NDJSON file (append-only)."""
    from config import settings

    path = (getattr(settings, "audit_log_path", None) or "").strip()
    if path:
        return Path(path)
    return DEFAULT_AUDIT_PATH


def append_entry(
    *,
    trace_id: str,
    incident_id: str,
    actor: str,
    tool: str,
    args: dict,
    decision: str = "allow",
    policy_result: str = "allow",
    outcome: str = "success",
    error_message: str | None = None,
) -> None:
    """
    Append one audit log entry. Append-only; no update/delete.
    actor: "agent" | "human"
    decision: e.g. allow, deny, escalate
    policy_result: OPA result — allow, deny, error (or "n/a" if no OPA yet)
    outcome: success, empty, failure, skipped
    error_message: optional short, safe description when outcome=failure
    """
    path = get_audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "incident_id": incident_id,
        "actor": actor,
        "tool": tool,
        "args_hash": _args_hash(args),
        "decision": decision,
        "policy_result": policy_result,
        "outcome": outcome,
    }
    if error_message:
        entry["error_message"] = error_message
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
