from __future__ import annotations

import asyncio

import config

from apps.load.burst_ingest import BurstConfig, summarize_burst


def test_summarize_burst_fields():
    out = summarize_burst(
        total_requests=10,
        successes=9,
        failures=1,
        latencies_ms=[10, 20, 30, 40, 50],
        accepted_sum=9,
        duplicates_sum=0,
        rejected_sum=0,
        duration_seconds=1.0,
    )
    assert out["total_requests"] == 10
    assert out["failure_rate"] == 0.1
    assert out["latency_ms"]["p95"] >= out["latency_ms"]["p50"]


def test_run_burst_against_local_testclient(api_client, monkeypatch):
    # Default unit tests run legacy file ingest; disable NATS branch explicitly.
    monkeypatch.setattr(config.settings, "nats_url", "")
    transport = __import__("httpx").ASGITransport(app=api_client.app)
    import httpx

    async def _run():
        cfg = BurstConfig(
            api_base_url="http://testserver",
            total_requests=40,
            concurrency=8,
            timeout_seconds=5.0,
        )
        sem = asyncio.Semaphore(max(1, cfg.concurrency))
        lat = []
        successes = failures = accepted_sum = duplicates_sum = rejected_sum = 0
        url = f"{cfg.api_base_url}/ingest?source={cfg.source}"
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:

            async def one(i: int):
                nonlocal successes, failures, accepted_sum, duplicates_sum, rejected_sum
                body = (
                    '{"event_id":"burst-t-%d","ts":"2026-05-07T10:00:00Z",'
                    '"channel":"power.bus_voltage","value":28.5}\n' % i
                )
                async with sem:
                    r = await client.post(
                        url,
                        content=body.encode("utf-8"),
                        headers={"Content-Type": "application/x-ndjson"},
                    )
                if 200 <= r.status_code < 300:
                    successes += 1
                    data = r.json()
                    accepted_sum += int(data.get("accepted") or 0)
                    duplicates_sum += int(data.get("duplicates") or 0)
                    rejected_sum += int(data.get("rejected") or 0)
                    lat.append(1.0)
                else:
                    failures += 1

            await asyncio.gather(*(one(i) for i in range(cfg.total_requests)))
        return summarize_burst(
            total_requests=cfg.total_requests,
            successes=successes,
            failures=failures,
            latencies_ms=lat,
            accepted_sum=accepted_sum,
            duplicates_sum=duplicates_sum,
            rejected_sum=rejected_sum,
            duration_seconds=0.5,
        )

    summary = asyncio.run(_run())
    assert summary["failures"] == 0
    assert summary["accepted_sum"] == 40
