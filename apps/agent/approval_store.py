"""
S2.5 — Approval requests store (file-based).

Persistent storage for approval_requests: create, list, get, approve, reject.
Idempotent: approve/reject on already-decided id returns success without re-execution.

When are files created? Only when the Act node runs a restricted step that OPA allows:
- Plan must contain a step with safe=false and action_type in {change_config, restart_service}.
- OPA must be running and return allow (policy allows that step; no "restart all" in action).
If OPA is down or denies → no create(), only escalation. See S2.4 / infra/opa/README.md.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_STORE_DIR = REPO_ROOT / "data" / "approvals"


def _store_dir() -> Path:
    from config import settings

    path = getattr(settings, "approval_store_path", None) or ""
    if path:
        return Path(path)
    return DEFAULT_STORE_DIR


def _path_for_id(request_id: str) -> Path:
    return _store_dir() / f"{request_id}.json"


def create(
    *,
    incident_id: str,
    step_index: int,
    step: dict[str, Any],
    reason: str = "restricted",
) -> str:
    """
    Persist a new approval request; return its id.
    """
    request_id = str(uuid.uuid4())
    store_dir = _store_dir()
    store_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "id": request_id,
        "incident_id": incident_id,
        "step_index": step_index,
        "step": step,
        "reason": reason,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decided_at": None,
        "decided_by": None,
    }
    with open(_path_for_id(request_id), "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return request_id


def list_requests(status: str | None = None) -> list[dict[str, Any]]:
    """Return all approval requests, optionally filtered by status (pending, approved, rejected)."""
    store_dir = _store_dir()
    if not store_dir.exists():
        return []
    out = []
    for p in store_dir.glob("*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                rec = json.load(f)
            if status is None or (rec.get("status") == status):
                out.append(rec)
        except (json.JSONDecodeError, OSError):
            continue
    out.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return out


def get_request(request_id: str) -> dict[str, Any] | None:
    """Return one approval request by id, or None if not found."""
    path = _path_for_id(request_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _update_status(
    request_id: str,
    new_status: str,
    decided_by: str,
) -> dict[str, Any] | None:
    rec = get_request(request_id)
    if rec is None:
        return None
    if rec.get("status") != "pending":
        return rec  # idempotent: already decided
    rec["status"] = new_status
    rec["decided_at"] = datetime.now(timezone.utc).isoformat()
    rec["decided_by"] = decided_by
    with open(_path_for_id(request_id), "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)
    return rec


def approve(request_id: str, decided_by: str) -> dict[str, Any] | None:
    """Set status to approved; return updated record or None. Idempotent if already approved/rejected."""
    return _update_status(request_id, "approved", decided_by)


def reject(request_id: str, decided_by: str) -> dict[str, Any] | None:
    """Set status to rejected; return updated record or None. Idempotent if already approved/rejected."""
    return _update_status(request_id, "rejected", decided_by)
