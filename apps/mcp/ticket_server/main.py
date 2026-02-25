"""
SpaceOps Mission Agent Lab — MCP Ticketing Server
Tool: create_ticket(title, body) — mock ticket store (append-only NDJSON).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from mcp.server.fastmcp import FastMCP


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


mcp = FastMCP("SpaceOps Ticketing", json_response=True)


@mcp.tool()
def create_ticket(title: str, body: str) -> Ticket:
    """
    Create a ticket with the given title and body.

    This is a mock implementation for S2: tickets are stored as append-only
    NDJSON in data/incidents/tickets.ndjson for later inspection or ingestion
    into a real ticketing system.
    """
    now = datetime.now(timezone.utc).isoformat()
    ticket_id = f"tkt-{now}"
    ticket: Ticket = {
        "id": ticket_id,
        "title": title,
        "body": body,
        "created_at": now,
    }
    _append_ticket(ticket)
    return ticket


if __name__ == "__main__":
    import uvicorn

    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=8003)
