#!/usr/bin/env python3
"""PS7.8 — Platform ops triage CLI (read-only collector + hypotheses)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Platform ops triage — read-only evidence + hypotheses (PS7.8)."
    )
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Emit snapshot JSON only (no hypotheses).",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Use a JSON snapshot fixture instead of live collection.",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL for /health and /dlq/telemetry.",
    )
    parser.add_argument(
        "--dlq-limit",
        type=int,
        default=20,
        help="Max DLQ rows in snapshot sample.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip optional LLM summary even when OPENAI_API_KEY is set.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Request remediate actions (MVP: blocked without --i-approve).",
    )
    parser.add_argument(
        "--i-approve",
        action="store_true",
        help="Explicit human approval for any write/apply path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON report to file (default: stdout).",
    )
    args = parser.parse_args()

    if args.apply and not args.i_approve:
        print(
            "ERROR: --apply requires explicit --i-approve (PS7.8 safety gate).",
            file=sys.stderr,
        )
        return 2

    if args.apply and args.i_approve:
        print(
            "NOTE: PS7.8 MVP is read-only; no write actions executed.",
            file=sys.stderr,
        )

    from apps.platform_ops.collector import collect_platform_ops_snapshot
    from apps.platform_ops.triage import build_triage_report

    if args.fixture:
        snapshot = _load_fixture(args.fixture)
    else:
        snapshot = collect_platform_ops_snapshot(
            api_base_url=args.api_url,
            dlq_limit=args.dlq_limit,
        )

    if args.collect_only:
        payload: dict[str, Any] = snapshot
    else:
        payload = build_triage_report(
            snapshot,
            use_llm=not args.no_llm,
        )

    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
