"""
SpaceOps Agent — CLI entrypoint (S1.7).
Usage: python -m apps.agent.run <incident_id> [payload_json]
"""
from __future__ import annotations

import json
import sys

from apps.agent.graph import run_pipeline


def main() -> None:
    incident_id = sys.argv[1] if len(sys.argv) > 1 else "inc-1"
    payload = {}
    if len(sys.argv) > 2:
        try:
            payload = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            payload = {"raw": sys.argv[2]}
    result = run_pipeline(incident_id, payload)
    report = result.get("report") or {}
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
