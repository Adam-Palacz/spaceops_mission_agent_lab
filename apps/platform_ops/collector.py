"""PS7.8 — read-only platform ops evidence collector (queue/DLQ/MCP)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from apps.common.http_resilience import get_circuit_snapshot
from apps.platform_ops.schema import SCHEMA_VERSION
from config import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _detect_environment_kind() -> str:
    if os.getenv("CI", "").lower() in ("1", "true", "yes"):
        return "ci"
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return "kubernetes"
    return "local"


def _http_probe(url: str, *, timeout: float = 3.0) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(4096).decode("utf-8", errors="replace")
            return {
                "reachable": True,
                "status_code": resp.status,
                "body_preview": body[:200],
            }
    except urllib.error.HTTPError as exc:
        return {
            "reachable": True,
            "status_code": exc.code,
            "error": str(exc.reason),
        }
    except Exception as exc:
        return {"reachable": False, "error": type(exc).__name__}


def _postgres_probe() -> dict[str, Any]:
    dsn = (getattr(settings, "postgres_dsn", "") or "").strip()
    if not dsn:
        return {"reachable": False, "error": "POSTGRES_DSN empty"}
    try:
        import psycopg2

        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return {"reachable": True}
    except Exception as exc:
        return {"reachable": False, "error": type(exc).__name__}


def _dlq_from_postgres(*, limit: int = 20) -> dict[str, Any]:
    dsn = (getattr(settings, "postgres_dsn", "") or "").strip()
    if not dsn:
        return {"available": False, "error": "POSTGRES_DSN empty"}
    try:
        import psycopg2

        from apps.workers.telemetry_persist import list_dlq_events

        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM dlq_events")
                total = int(cur.fetchone()[0])
                cur.execute(
                    """
                    SELECT reason, COUNT(*) AS cnt
                    FROM dlq_events
                    GROUP BY reason
                    ORDER BY cnt DESC
                    """
                )
                reason_counts = {str(row[0]): int(row[1]) for row in cur.fetchall()}
            sample = list_dlq_events(conn, limit=min(max(limit, 1), 100))
        return {
            "available": True,
            "total_count": total,
            "reason_counts": reason_counts,
            "sample": sample,
        }
    except Exception as exc:
        return {"available": False, "error": type(exc).__name__}


def _dlq_from_api(api_base_url: str, *, limit: int = 20) -> dict[str, Any]:
    url = f"{api_base_url.rstrip('/')}/dlq/telemetry?limit={limit}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        events = payload.get("dlq_events") or []
        reason_counts: dict[str, int] = {}
        for row in events:
            reason = str(row.get("reason") or "unknown")
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        return {
            "available": True,
            "total_count": int(payload.get("count") or len(events)),
            "reason_counts": reason_counts,
            "sample": events,
            "source": "api",
        }
    except Exception as exc:
        return {"available": False, "error": type(exc).__name__, "source": "api"}


def _mcp_endpoints() -> list[dict[str, Any]]:
    endpoints: list[tuple[str, str]] = []
    for name, url in (
        ("telemetry_mcp", getattr(settings, "telemetry_mcp_url", "")),
        ("kb_mcp", getattr(settings, "kb_mcp_url", "")),
        ("ticket_mcp", getattr(settings, "ticket_mcp_url", "")),
        ("gitops_mcp", getattr(settings, "gitops_mcp_url", "")),
    ):
        cleaned = (url or "").strip()
        if cleaned:
            endpoints.append((name, cleaned))
    out: list[dict[str, Any]] = []
    for name, url in endpoints:
        probe = _http_probe(url)
        out.append({"name": name, "url": url, **probe})
    return out


def collect_platform_ops_snapshot(
    *,
    api_base_url: str = "http://localhost:8000",
    dlq_limit: int = 20,
    prefer_postgres_dlq: bool = True,
) -> dict[str, Any]:
    """Gather read-only operational evidence for platform ops triage."""
    api_health = _http_probe(f"{api_base_url.rstrip('/')}/health")

    dlq: dict[str, Any]
    if prefer_postgres_dlq:
        dlq = _dlq_from_postgres(limit=dlq_limit)
        if not dlq.get("available"):
            dlq = _dlq_from_api(api_base_url, limit=dlq_limit)
    else:
        dlq = _dlq_from_api(api_base_url, limit=dlq_limit)
        if not dlq.get("available"):
            dlq = _dlq_from_postgres(limit=dlq_limit)

    circuits = get_circuit_snapshot()
    mcp_open = [
        c
        for c in circuits
        if c.get("state") == "open" and str(c.get("key", "")).startswith("mcp")
    ]
    mcp_endpoints = _mcp_endpoints()

    domains: list[str] = []
    if dlq.get("available") and int(dlq.get("total_count") or 0) > 0:
        domains.append("queue_dlq")
    if mcp_open or any(not ep.get("reachable") for ep in mcp_endpoints):
        domains.append("mcp_transport")
    if not domains:
        domains.append("general")

    return {
        "schema_version": SCHEMA_VERSION,
        "collected_at": _utc_now(),
        "environment": {
            "kind": _detect_environment_kind(),
            "api_base_url": api_base_url,
            "nats_url_configured": bool(
                (getattr(settings, "nats_url", "") or "").strip()
            ),
        },
        "services": {
            "api": {"url": api_base_url, **api_health},
            "postgres": _postgres_probe(),
        },
        "queue": {
            "dlq": dlq,
        },
        "mcp": {
            "endpoints": mcp_endpoints,
            "circuit_breakers": circuits,
            "open_mcp_circuits": mcp_open,
        },
        "symptom_domains": domains,
    }
