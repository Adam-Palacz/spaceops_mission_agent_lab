"""
SpaceOps Mission Agent Lab — MCP Ticketing Server
Tool: create_ticket(title, body) — mock ticket store (append-only NDJSON).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from opentelemetry.trace import SpanKind, Status, StatusCode

from apps.telemetry import get_tracer
from apps.tracing import extract_w3c_context_from_headers


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_INCIDENTS = REPO_ROOT / "data" / "incidents"
TICKETS_FILE = DATA_INCIDENTS / "tickets.ndjson"


class Ticket(TypedDict):
    id: str
    title: str
    body: str
    created_at: str


def _append_ticket(ticket: Ticket) -> None:
    """Append a single ticket as NDJSON line to the tickets file."""
    DATA_INCIDENTS.mkdir(parents=True, exist_ok=True)
    with open(TICKETS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(ticket, ensure_ascii=False) + "\n")


mcp = FastMCP(
    "SpaceOps Ticketing",
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
def create_ticket(title: str, body: str, ctx: Context | None = None) -> Ticket:
    """
    Create a ticket with the given title and body.

    This is a mock implementation for S2: tickets are stored as append-only
    NDJSON in data/incidents/tickets.ndjson for later inspection or ingestion
    into a real ticketing system.
    """
    parent_context = extract_w3c_context_from_headers(_extract_headers_from_ctx(ctx))
    tracer = get_tracer("apps.mcp.ticket")
    with tracer.start_as_current_span(
        "mcp.ticket.create_ticket", context=parent_context, kind=SpanKind.SERVER
    ) as span:
        span.set_attribute("tool", "create_ticket")
        try:
            now = datetime.now(timezone.utc).isoformat()
            ticket_id = f"tkt-{now}"
            ticket: Ticket = {
                "id": ticket_id,
                "title": title,
                "body": body,
                "created_at": now,
            }
            _append_ticket(ticket)
            span.set_attribute("outcome", "success")
            return ticket
        except Exception:
            span.set_status(Status(StatusCode.ERROR, "create_ticket failed"))
            span.set_attribute("outcome", "failure")
            raise


if __name__ == "__main__":
    import uvicorn

    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=8003)
