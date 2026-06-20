#!/usr/bin/env python3
"""PS7.7 — Print deterministic multi-cloud burst routing scenarios (no live cloud B)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _scenarios() -> list[tuple[str, Any, str]]:
    from apps.llm_burst_routing import BurstRoutingSignals

    return [
        (
            "kill_switch",
            BurstRoutingSignals(
                kill_switch=True,
                burst_enabled=True,
                primary_backend="openai",
                burst_backend="gpu",
                primary_healthy=True,
                burst_healthy=True,
                budget_ok=True,
                burst_within_cost_ceiling=True,
                burst_latency_p95_ms=100,
                latency_sla_ms=500,
            ),
            "kill_switch_active",
        ),
        (
            "burst_disabled",
            BurstRoutingSignals(
                kill_switch=False,
                burst_enabled=False,
                primary_backend="openai",
                burst_backend="gpu",
                primary_healthy=True,
                burst_healthy=True,
                budget_ok=True,
                burst_within_cost_ceiling=True,
                burst_latency_p95_ms=100,
                latency_sla_ms=500,
            ),
            "burst_disabled",
        ),
        (
            "budget_exceeded",
            BurstRoutingSignals(
                kill_switch=False,
                burst_enabled=True,
                primary_backend="openai",
                burst_backend="gpu",
                primary_healthy=True,
                burst_healthy=True,
                budget_ok=False,
                burst_within_cost_ceiling=True,
                burst_latency_p95_ms=100,
                latency_sla_ms=500,
            ),
            "budget_exceeded",
        ),
        (
            "burst_unavailable",
            BurstRoutingSignals(
                kill_switch=False,
                burst_enabled=True,
                primary_backend="openai",
                burst_backend="gpu",
                primary_healthy=True,
                burst_healthy=False,
                budget_ok=True,
                burst_within_cost_ceiling=True,
                burst_latency_p95_ms=100,
                latency_sla_ms=500,
            ),
            "burst_unavailable",
        ),
        (
            "burst_policy_match",
            BurstRoutingSignals(
                kill_switch=False,
                burst_enabled=True,
                primary_backend="openai",
                burst_backend="gpu",
                primary_healthy=True,
                burst_healthy=True,
                budget_ok=True,
                burst_within_cost_ceiling=True,
                burst_latency_p95_ms=120,
                latency_sla_ms=500,
            ),
            "burst_policy_match",
        ),
        (
            "primary_unhealthy_burst_takeover",
            BurstRoutingSignals(
                kill_switch=False,
                burst_enabled=True,
                primary_backend="openai",
                burst_backend="gpu",
                primary_healthy=False,
                burst_healthy=True,
                budget_ok=True,
                burst_within_cost_ceiling=True,
                burst_latency_p95_ms=120,
                latency_sla_ms=500,
            ),
            "primary_unhealthy_burst_takeover",
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Simulate multi-cloud burst routing decisions (PS7.7)."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON array of scenario results.",
    )
    args = parser.parse_args()

    from apps.llm_burst_routing import decide_burst_route

    rows: list[dict[str, object]] = []
    for name, signals, expected_reason in _scenarios():
        decision = decide_burst_route(signals)
        ok = decision.backend_routing_reason == expected_reason
        row = {
            "scenario": name,
            "backend_to_use": decision.backend_to_use,
            "backend_routing_reason": decision.backend_routing_reason,
            "used_burst": decision.used_burst,
            "fallback_to_primary": decision.fallback_to_primary,
            "expected_reason": expected_reason,
            "pass": ok,
        }
        rows.append(row)
        if not args.json:
            status = "OK" if ok else "FAIL"
            print(
                f"{status} {name}: backend={decision.backend_to_use} "
                f"reason={decision.backend_routing_reason}"
            )

    if args.json:
        print(json.dumps(rows, indent=2))

    return 0 if all(r["pass"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
