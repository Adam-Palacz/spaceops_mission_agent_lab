from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from apps.load.burst_ingest import BurstConfig, run_burst


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PS3.5 burst/backpressure scenario for /ingest telemetry."
    )
    parser.add_argument("--api-base-url", default="http://localhost:8000")
    parser.add_argument("--source", default="telemetry")
    parser.add_argument("--total-requests", type=int, default=300)
    parser.add_argument("--concurrency", type=int, default=30)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--max-failure-rate", type=float, default=0.05)
    parser.add_argument("--max-p95-ms", type=float, default=1500.0)
    parser.add_argument("--output-json", default="")
    args = parser.parse_args()

    cfg = BurstConfig(
        api_base_url=args.api_base_url,
        source=args.source,
        total_requests=max(1, args.total_requests),
        concurrency=max(1, args.concurrency),
        timeout_seconds=max(0.1, args.timeout_seconds),
    )
    summary = asyncio.run(run_burst(cfg))
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if args.output_json.strip():
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    failure_rate = float(summary.get("failure_rate") or 0.0)
    p95 = float((summary.get("latency_ms") or {}).get("p95") or 0.0)
    if failure_rate > float(args.max_failure_rate):
        print(
            f"Burst FAILED: failure_rate={failure_rate:.4f} > max={float(args.max_failure_rate):.4f}"
        )
        return 2
    if p95 > float(args.max_p95_ms):
        print(f"Burst FAILED: p95_ms={p95:.2f} > max={float(args.max_p95_ms):.2f}")
        return 2
    print("Burst scenario PASSED thresholds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
