"""
Export JSON Schemas for contract models.

Usage:
    python scripts/export_contract_schemas.py
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "contracts" / "schemas" / "v1"


def _write_schema(name: str, schema: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.schema.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main() -> None:
    from apps.contracts.v1 import (
        AgentReportV1,
        EscalationPacketV1,
        IncidentV1,
        TelemetryEventV1,
    )

    _write_schema("telemetry_event", TelemetryEventV1.model_json_schema())
    _write_schema("incident", IncidentV1.model_json_schema())
    _write_schema("agent_report", AgentReportV1.model_json_schema())
    _write_schema("escalation_packet", EscalationPacketV1.model_json_schema())
    print(f"Exported contract schemas to {OUT_DIR}")


if __name__ == "__main__":
    main()
