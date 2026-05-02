"""
SpaceOps Mission Agent Lab — MCP Telemetry Server
Tool: query_telemetry(time_range_start, time_range_end, channels) — reads from data/telemetry (NDJSON).
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from opentelemetry.trace import SpanKind, Status, StatusCode

from apps.telemetry import get_tracer
from apps.tracing import extract_w3c_context_from_headers

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_TELEMETRY = REPO_ROOT / "data" / "telemetry"


def _load_telemetry_records() -> list[dict]:
    """Load all NDJSON records from data/telemetry/*.ndjson."""
    records: list[dict] = []
    if not DATA_TELEMETRY.exists():
        return records
    for path in sorted(DATA_TELEMETRY.glob("*.ndjson")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def _parse_ts(ts: str) -> str | None:
    """Return ts as-is if present; for filtering we compare ISO8601 strings (lexicographic order)."""
    if not ts or not isinstance(ts, str):
        return None
    return ts.strip()


mcp = FastMCP(
    "SpaceOps Telemetry",
    json_response=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


def _extract_headers_from_ctx(ctx: Context | None) -> dict[str, str]:
    if ctx is None:
        return {}
    request = getattr(ctx.request_context, "request", None)
    headers = getattr(request, "headers", None)
    if headers is None:
        return {}
    return {str(k): str(v) for k, v in headers.items()}


@mcp.tool()
def query_telemetry(
    time_range_start: str,
    time_range_end: str,
    channels: list[str] | None = None,
    ctx: Context | None = None,
) -> list[dict]:
    """
    Query telemetry data within a time range, optionally filtered by channel names.
    Reads from data/telemetry (fixtures and ingest files). All times in ISO8601 (e.g. 2025-02-14T10:00:00Z).
    Returns list of records with ts, channel, value, subsystem, unit.
    """
    parent_context = extract_w3c_context_from_headers(
        _extract_headers_from_ctx(ctx) if ctx else {}
    )
    tracer = get_tracer("apps.mcp.telemetry")
    with tracer.start_as_current_span(
        "mcp.telemetry.query_telemetry",
        context=parent_context,
        kind=SpanKind.SERVER,
    ) as span:
        span.set_attribute("tool", "query_telemetry")
        start = _parse_ts(time_range_start)
        end = _parse_ts(time_range_end)
        if not start or not end:
            return []
        records = _load_telemetry_records()
        out: list[dict] = []
        for r in records:
            if not isinstance(r, dict):
                continue
            ts = _parse_ts(r.get("ts") or r.get("timestamp") or "")
            if not ts or ts < start or ts > end:
                continue
            if channels:
                ch = r.get("channel") or r.get("channel_id")
                if ch not in channels:
                    continue
            out.append(r)
        span.set_attribute("outcome", "success" if out else "empty")
        try:
            span.set_attribute("result_count", len(out))
        except Exception:
            span.set_status(Status(StatusCode.ERROR, "span attribute error"))
        return out


if __name__ == "__main__":
    import uvicorn

    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)
