from __future__ import annotations

import asyncio
import statistics
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class BurstConfig:
    api_base_url: str
    source: str = "telemetry"
    total_requests: int = 200
    concurrency: int = 20
    timeout_seconds: float = 10.0


def _telemetry_ndjson_line(i: int) -> str:
    return (
        '{"event_id":"burst-%d","ts":"2026-05-07T10:00:00Z",'
        '"channel":"power.bus_voltage","value":28.5}\n' % i
    )


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    idx = (len(sorted_values) - 1) * p
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = idx - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


def summarize_burst(
    *,
    total_requests: int,
    successes: int,
    failures: int,
    latencies_ms: list[float],
    accepted_sum: int,
    duplicates_sum: int,
    rejected_sum: int,
    duration_seconds: float,
) -> dict[str, Any]:
    lat_sorted = sorted(latencies_ms)
    p50 = _percentile(lat_sorted, 0.50)
    p95 = _percentile(lat_sorted, 0.95)
    rps = (total_requests / duration_seconds) if duration_seconds > 0 else 0.0
    failure_rate = (failures / total_requests) if total_requests > 0 else 0.0
    return {
        "total_requests": total_requests,
        "successes": successes,
        "failures": failures,
        "failure_rate": round(failure_rate, 6),
        "accepted_sum": accepted_sum,
        "duplicates_sum": duplicates_sum,
        "rejected_sum": rejected_sum,
        "duration_seconds": round(duration_seconds, 3),
        "requests_per_second": round(rps, 2),
        "latency_ms": {
            "mean": round(statistics.mean(latencies_ms), 2) if latencies_ms else 0.0,
            "p50": round(p50, 2),
            "p95": round(p95, 2),
        },
    }


async def run_burst(config: BurstConfig) -> dict[str, Any]:
    sem = asyncio.Semaphore(max(1, config.concurrency))
    latencies_ms: list[float] = []
    successes = 0
    failures = 0
    accepted_sum = 0
    duplicates_sum = 0
    rejected_sum = 0
    url = f"{config.api_base_url.rstrip('/')}/ingest?source={config.source}"
    timeout = httpx.Timeout(config.timeout_seconds)

    async with httpx.AsyncClient(timeout=timeout) as client:

        async def one(i: int) -> None:
            nonlocal successes, failures, accepted_sum, duplicates_sum, rejected_sum
            body = _telemetry_ndjson_line(i)
            t0 = time.perf_counter()
            async with sem:
                try:
                    resp = await client.post(
                        url,
                        content=body.encode("utf-8"),
                        headers={"Content-Type": "application/x-ndjson"},
                    )
                except Exception:
                    failures += 1
                    return
            dt_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(dt_ms)
            if 200 <= resp.status_code < 300:
                successes += 1
                try:
                    payload = resp.json()
                except Exception:
                    payload = {}
                accepted_sum += int(payload.get("accepted") or 0)
                duplicates_sum += int(payload.get("duplicates") or 0)
                rejected_sum += int(payload.get("rejected") or 0)
            else:
                failures += 1

        started = time.perf_counter()
        await asyncio.gather(*(one(i) for i in range(config.total_requests)))
        duration = time.perf_counter() - started

    return summarize_burst(
        total_requests=config.total_requests,
        successes=successes,
        failures=failures,
        latencies_ms=latencies_ms,
        accepted_sum=accepted_sum,
        duplicates_sum=duplicates_sum,
        rejected_sum=rejected_sum,
        duration_seconds=duration,
    )
