#!/usr/bin/env python3
"""
PS4.7 — Run local CI hard/soft gates with ordered summary (mirrors ci.yml policy).

Usage (repo root):
  python scripts/ci_gate_runner.py --hard-only
  python scripts/ci_gate_runner.py --hard-only --gate safety-opa-hitl
  python scripts/ci_gate_runner.py --include-soft
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.ci_gating import (  # noqa: E402
    default_hard_gates,
    default_soft_gates,
    format_gate_summary,
    run_gates,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PS4.7 CI gate policy locally.")
    parser.add_argument(
        "--hard-only",
        action="store_true",
        help="Run hard gates only (default without --include-soft).",
    )
    parser.add_argument(
        "--include-soft",
        action="store_true",
        help="Also run soft quality signals after hard gates.",
    )
    parser.add_argument(
        "--gate",
        action="append",
        default=[],
        help="Run only these gate_id values (repeatable).",
    )
    parser.add_argument(
        "--write-summary",
        type=Path,
        default=None,
        help="Write markdown summary to this path.",
    )
    args = parser.parse_args()

    gates = default_hard_gates()
    if args.include_soft:
        gates = gates + default_soft_gates()
    elif not args.hard_only and not args.gate:
        gates = default_hard_gates()

    if args.gate:
        wanted = set(args.gate)
        gates = [g for g in gates if g.gate_id in wanted]
        missing = wanted - {g.gate_id for g in gates}
        if missing:
            print(f"Unknown gate id(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 2

    print("Running CI gates (ordered):")
    for g in gates:
        print(f"  [{g.tier}] {g.gate_id}: {g.title}")

    exit_code, report = run_gates(gates, cwd=str(REPO_ROOT))
    summary = format_gate_summary(report)
    print()
    print(summary)

    if args.write_summary:
        args.write_summary.parent.mkdir(parents=True, exist_ok=True)
        args.write_summary.write_text(summary, encoding="utf-8")
        print(f"Wrote summary: {args.write_summary}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
