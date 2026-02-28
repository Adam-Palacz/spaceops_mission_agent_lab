#!/usr/bin/env python3
"""
Seed one pending approval request into data/approvals for testing the Approval API.

Run from repo root:
  python scripts/seed_approval_request.py

Then use GET /approvals (with X-API-Key) and POST /approvals/<id>/approve or /reject.
Does not require running the agent or OPA.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    REPO_ROOT = Path(__file__).resolve().parent.parent
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from apps.agent.approval_store import _store_dir, create

    request_id = create(
        incident_id="seed-test-incident",
        step_index=0,
        step={
            "action": "Increase heater setpoint on unit A (test seed)",
            "action_type": "change_config",
            "safe": False,
        },
        reason="restricted",
    )
    store_dir = _store_dir()
    print(f"Created approval request: {request_id}")
    print(f"Store dir: {store_dir}")
    print(f"File: {store_dir / (request_id + '.json')}")
    print(
        "Test with: GET /approvals and POST /approvals/{id}/approve (header X-API-Key: your APPROVAL_API_KEY)"
    )


if __name__ == "__main__":
    main()
