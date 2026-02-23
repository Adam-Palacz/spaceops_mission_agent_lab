"""
SpaceOps Agent — MCP client helpers to call Telemetry and KB servers (S1.7).
"""
from __future__ import annotations

import asyncio
import json

from config import settings

# Optional MCP client imports
try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False


async def _call_telemetry_mcp(time_range_start: str, time_range_end: str, channels: list[str] | None = None) -> list[dict]:
    if not _MCP_AVAILABLE:
        return []
    url = settings.telemetry_mcp_url
    try:
        async with streamable_http_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(
                    "query_telemetry",
                    arguments={
                        "time_range_start": time_range_start,
                        "time_range_end": time_range_end,
                        "channels": channels or [],
                    },
                )
                if result.isError:
                    return []
                if result.structuredContent:
                    return list(result.structuredContent) if isinstance(result.structuredContent, list) else [result.structuredContent]
                if result.content:
                    text = result.content[0].text if result.content else ""
                    return json.loads(text) if text.strip().startswith("[") else []
    except Exception:
        return []
    return []


async def _call_kb_runbooks_mcp(query: str, limit: int = 5) -> list[dict]:
    if not _MCP_AVAILABLE:
        return []
    url = settings.kb_mcp_url
    try:
        async with streamable_http_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("search_runbooks", arguments={"query": query, "limit": limit})
                if result.isError:
                    return []
                if result.structuredContent:
                    return list(result.structuredContent) if isinstance(result.structuredContent, list) else [result.structuredContent]
                if result.content:
                    text = result.content[0].text if result.content else ""
                    return json.loads(text) if text.strip().startswith("[") else []
    except Exception:
        return []
    return []


async def _call_kb_postmortems_mcp(signature: str, limit: int = 5) -> list[dict]:
    if not _MCP_AVAILABLE:
        return []
    url = settings.kb_mcp_url
    try:
        async with streamable_http_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("search_postmortems", arguments={"signature": signature, "limit": limit})
                if result.isError:
                    return []
                if result.structuredContent:
                    return list(result.structuredContent) if isinstance(result.structuredContent, list) else [result.structuredContent]
                if result.content:
                    text = result.content[0].text if result.content else ""
                    return json.loads(text) if text.strip().startswith("[") else []
    except Exception:
        return []
    return []


def call_telemetry(time_range_start: str, time_range_end: str, channels: list[str] | None = None) -> list[dict]:
    """Sync wrapper for query_telemetry MCP call."""
    return asyncio.run(_call_telemetry_mcp(time_range_start, time_range_end, channels))


def call_search_runbooks(query: str, limit: int = 5) -> list[dict]:
    """Sync wrapper for search_runbooks MCP call."""
    return asyncio.run(_call_kb_runbooks_mcp(query, limit))


def call_search_postmortems(signature: str, limit: int = 5) -> list[dict]:
    """Sync wrapper for search_postmortems MCP call."""
    return asyncio.run(_call_kb_postmortems_mcp(signature, limit))


async def gather_investigate(
    time_range_start: str,
    time_range_end: str,
    query: str,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Async: call telemetry + runbooks + postmortems in parallel."""
    telemetry, runbooks, postmortems = await asyncio.gather(
        _call_telemetry_mcp(time_range_start, time_range_end),
        _call_kb_runbooks_mcp(query, 5),
        _call_kb_postmortems_mcp(query, 5),
    )
    return telemetry, runbooks, postmortems


def signature_from_payload(payload: dict | None) -> str:
    """Build a search signature from incident payload for KB search."""
    if not payload:
        return "anomaly"
    if isinstance(payload.get("subsystem"), str):
        return str(payload.get("subsystem", "")).lower() or "anomaly"
    if isinstance(payload.get("message"), str):
        return payload["message"][:100]
    return "anomaly"
