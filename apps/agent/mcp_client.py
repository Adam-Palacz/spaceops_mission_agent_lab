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


async def _call_telemetry_mcp(
    time_range_start: str, time_range_end: str, channels: list[str] | None = None
) -> list[dict]:
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
                # MCP SDK may use is_error (snake_case) or isError (camelCase)
                if getattr(result, "is_error", False) or getattr(
                    result, "isError", False
                ):
                    return []
                # Prefer structured_content (snake_case); fallback structuredContent (camelCase)
                structured = getattr(result, "structured_content", None) or getattr(
                    result, "structuredContent", None
                )
                if structured is not None:
                    if (
                        isinstance(structured, dict)
                        and "result" in structured
                        and isinstance(structured["result"], list)
                    ):
                        return structured["result"]
                    if isinstance(structured, list):
                        return structured
                    return [structured]
                content = getattr(result, "content", None) or []
                for part in content:
                    for attr in ("json", "data"):
                        payload = getattr(part, attr, None)
                        if isinstance(payload, list):
                            return payload
                        if payload is not None:
                            return payload if isinstance(payload, list) else [payload]
                collected: list[dict] = []
                for part in content:
                    text = (
                        getattr(part, "text", None)
                        or (part.get("text", "") if isinstance(part, dict) else "")
                        or ""
                    )
                    if not isinstance(text, str):
                        continue
                    text = text.strip()
                    if not text:
                        continue
                    try:
                        if text.startswith("["):
                            return json.loads(text)
                        if text.startswith("{"):
                            obj = json.loads(text)
                            if isinstance(obj, dict):
                                if "result" in obj and isinstance(obj["result"], list):
                                    return obj["result"]
                                if len(obj) == 1:
                                    only = next(iter(obj.values()))
                                    if isinstance(only, list):
                                        return only
                            collected.append(obj)
                    except json.JSONDecodeError:
                        pass
                if collected:
                    if (
                        len(collected) == 1
                        and isinstance(collected[0], dict)
                        and "result" in collected[0]
                    ):
                        inner = collected[0]["result"]
                        if isinstance(inner, list):
                            return inner
                    return collected
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
                result = await session.call_tool(
                    "search_runbooks", arguments={"query": query, "limit": limit}
                )
                if getattr(result, "is_error", False) or getattr(
                    result, "isError", False
                ):
                    return []
                structured = getattr(result, "structured_content", None) or getattr(
                    result, "structuredContent", None
                )
                if structured is not None:
                    if (
                        isinstance(structured, dict)
                        and "result" in structured
                        and isinstance(structured["result"], list)
                    ):
                        return structured["result"]
                    if isinstance(structured, list):
                        return structured
                    return [structured]
                content = getattr(result, "content", None) or []
                for part in content:
                    for attr in ("json", "data"):
                        payload = getattr(part, attr, None)
                        if isinstance(payload, list):
                            return payload
                        if payload is not None:
                            return payload if isinstance(payload, list) else [payload]
                collected: list[dict] = []
                for part in content:
                    text = (
                        getattr(part, "text", None)
                        or (part.get("text", "") if isinstance(part, dict) else "")
                        or ""
                    )
                    if not isinstance(text, str):
                        continue
                    text = text.strip()
                    if not text:
                        continue
                    try:
                        if text.startswith("["):
                            return json.loads(text)
                        if text.startswith("{"):
                            obj = json.loads(text)
                            if isinstance(obj, dict):
                                if "result" in obj and isinstance(obj["result"], list):
                                    return obj["result"]
                                if len(obj) == 1:
                                    only = next(iter(obj.values()))
                                    if isinstance(only, list):
                                        return only
                            collected.append(obj)
                    except json.JSONDecodeError:
                        pass
                if collected:
                    if (
                        len(collected) == 1
                        and isinstance(collected[0], dict)
                        and "result" in collected[0]
                    ):
                        inner = collected[0]["result"]
                        if isinstance(inner, list):
                            return inner
                    return collected
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
                result = await session.call_tool(
                    "search_postmortems",
                    arguments={"signature": signature, "limit": limit},
                )
                if getattr(result, "is_error", False) or getattr(
                    result, "isError", False
                ):
                    return []
                structured = getattr(result, "structured_content", None) or getattr(
                    result, "structuredContent", None
                )
                if structured is not None:
                    if (
                        isinstance(structured, dict)
                        and "result" in structured
                        and isinstance(structured["result"], list)
                    ):
                        return structured["result"]
                    if isinstance(structured, list):
                        return structured
                    return [structured]
                content = getattr(result, "content", None) or []
                for part in content:
                    for attr in ("json", "data"):
                        payload = getattr(part, attr, None)
                        if isinstance(payload, list):
                            return payload
                        if payload is not None:
                            return payload if isinstance(payload, list) else [payload]
                collected: list[dict] = []
                for part in content:
                    text = (
                        getattr(part, "text", None)
                        or (part.get("text", "") if isinstance(part, dict) else "")
                        or ""
                    )
                    if not isinstance(text, str):
                        continue
                    text = text.strip()
                    if not text:
                        continue
                    try:
                        if text.startswith("["):
                            return json.loads(text)
                        if text.startswith("{"):
                            obj = json.loads(text)
                            if isinstance(obj, dict):
                                if "result" in obj and isinstance(obj["result"], list):
                                    return obj["result"]
                                if len(obj) == 1:
                                    only = next(iter(obj.values()))
                                    if isinstance(only, list):
                                        return only
                            collected.append(obj)
                    except json.JSONDecodeError:
                        pass
                if collected:
                    if (
                        len(collected) == 1
                        and isinstance(collected[0], dict)
                        and "result" in collected[0]
                    ):
                        inner = collected[0]["result"]
                        if isinstance(inner, list):
                            return inner
                    return collected
    except Exception:
        return []
    return []


def _decode_single_result(result, *, content_attr: str = "content") -> dict | None:
    """Decode MCP tool result to a single dict (e.g. create_ticket, create_pr)."""
    if getattr(result, "is_error", False) or getattr(result, "isError", False):
        return None
    # Some MCP SDKs expose parsed body as .data
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return data
    structured = getattr(result, "structured_content", None) or getattr(
        result, "structuredContent", None
    )
    if isinstance(structured, dict):
        if "result" in structured and isinstance(structured["result"], dict):
            return structured["result"]
        return structured
    content = getattr(result, content_attr, None) or []
    for part in content:
        text = (
            getattr(part, "text", None)
            or (part.get("text", "") if isinstance(part, dict) else "")
            or ""
        )
        if isinstance(text, str) and text.strip().startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
    return None


async def _call_ticket_mcp(title: str, body: str) -> dict | None:
    if not _MCP_AVAILABLE:
        return None
    url = getattr(settings, "ticket_mcp_url", "http://localhost:8003/mcp")
    try:
        async with streamable_http_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(
                    "create_ticket", arguments={"title": title, "body": body}
                )
                return _decode_single_result(result)
    except Exception:
        return None


async def _call_gitops_mcp(
    repo_path: str | None, branch: str, files: list[dict]
) -> dict | None:
    if not _MCP_AVAILABLE:
        return None
    url = getattr(settings, "gitops_mcp_url", "http://localhost:8004/mcp")
    try:
        async with streamable_http_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(
                    "create_pr",
                    arguments={
                        "repo_path": repo_path,
                        "branch": branch,
                        "files": files,
                    },
                )
                return _decode_single_result(result)
    except Exception:
        return None


def call_telemetry(
    time_range_start: str, time_range_end: str, channels: list[str] | None = None
) -> list[dict]:
    """Sync wrapper for query_telemetry MCP call."""
    return asyncio.run(_call_telemetry_mcp(time_range_start, time_range_end, channels))


def call_create_ticket(title: str, body: str) -> dict | None:
    """Sync wrapper for create_ticket MCP call (S2.2). Returns ticket dict or None."""
    return asyncio.run(_call_ticket_mcp(title, body))


def call_create_pr(
    repo_path: str | None, branch: str, files: list[dict]
) -> dict | None:
    """Sync wrapper for create_pr MCP call (S2.2). Returns result dict or None."""
    return asyncio.run(_call_gitops_mcp(repo_path, branch, files))


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
