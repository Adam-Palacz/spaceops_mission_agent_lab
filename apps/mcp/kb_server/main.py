"""
SpaceOps Mission Agent Lab — MCP KB Server
Tools: search_runbooks(query), search_postmortems(signature) — RAG over pgvector.
Requires: Postgres with kb_chunks populated (run index_kb.py); set OPENAI_API_KEY in .env.
"""

from __future__ import annotations

from typing import TypedDict

import numpy as np
from langchain_openai import OpenAIEmbeddings
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from opentelemetry.trace import SpanKind, Status, StatusCode
import psycopg2
from pgvector.psycopg2 import register_vector

from config import settings
from apps.common.reranker import rerank_chunks
from apps.telemetry import get_tracer
from apps.tracing import extract_w3c_context_from_headers

EMBEDDING_DIM = 1536


def get_connection():
    """
    Return a Postgres connection for KB RAG.

    S1.17: Fail fast with a clear error if Postgres is not configured.
    Core app (API/agent without KB) should not require POSTGRES_PASSWORD, but KB server does.
    """
    if (
        not settings.database_url
        and not getattr(settings, "postgres_password", "").strip()
    ):
        raise RuntimeError(
            "Postgres is required for KB server (RAG). "
            "Set DATABASE_URL or POSTGRES_PASSWORD/POSTGRES_* in the environment or .env."
        )
    return psycopg2.connect(settings.postgres_dsn)


class ChunkResult(TypedDict):
    content: str
    doc_id: str


def _search(embedding: list[float], doc_type: str, limit: int = 5) -> list[ChunkResult]:
    conn = get_connection()
    register_vector(conn)
    # pgvector psycopg2 adapter binds ndarray as vector; plain list becomes numeric[] and breaks <=>.
    query_vec = np.asarray(embedding, dtype=np.float32)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT content, doc_id
            FROM kb_chunks
            WHERE doc_type = %s
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (doc_type, query_vec, limit),
        )
        rows = cur.fetchall()
    conn.close()
    return [ChunkResult(content=r[0], doc_id=r[1]) for r in rows]


mcp = FastMCP(
    "SpaceOps KB",
    json_response=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)
_embeddings = None


def _extract_headers_from_ctx(ctx: Context | None) -> dict[str, str]:
    if ctx is None:
        return {}
    request = getattr(ctx.request_context, "request", None)
    headers = getattr(request, "headers", None)
    if headers is None:
        return {}
    return {str(k): str(v) for k, v in headers.items()}


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required; set it in .env or environment."
            )
        _embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.openai_api_key,
        )
    return _embeddings


@mcp.tool()
def search_runbooks(
    query: str, limit: int = 5, ctx: Context | None = None
) -> list[ChunkResult]:
    """
    Semantic search over runbooks. Returns matching text chunks and their doc_id (filename) for citations.
    Use for investigating anomalies: e.g. "power bus voltage", "thermal temperature high".
    """
    parent_context = extract_w3c_context_from_headers(_extract_headers_from_ctx(ctx))
    tracer = get_tracer("apps.mcp.kb")
    with tracer.start_as_current_span(
        "mcp.kb.search_runbooks", context=parent_context, kind=SpanKind.SERVER
    ) as span:
        span.set_attribute("tool", "search_runbooks")
        if not query or not query.strip():
            span.set_attribute("outcome", "empty")
            return []
        try:
            vec = _get_embeddings().embed_query(query.strip())
            retrieve_k = max(
                int(limit), int(getattr(settings, "kb_reranker_retrieve_k", limit))
            )
            candidates = _search(vec, "runbook", limit=retrieve_k)
            if getattr(settings, "kb_reranker_enabled", False):
                mode = str(getattr(settings, "kb_reranker_mode", "lexical")).strip()
                ranked = rerank_chunks(query, list(candidates), mode=mode)
                ranked = ranked[:limit]
                out = [
                    ChunkResult(content=r["content"], doc_id=r["doc_id"])
                    for r in ranked
                ]
                span.set_attribute("outcome", "success" if out else "empty")
                return out
            out = candidates[:limit]
            span.set_attribute("outcome", "success" if out else "empty")
            return out
        except Exception:
            span.set_status(Status(StatusCode.ERROR, "search_runbooks failed"))
            span.set_attribute("outcome", "failure")
            raise


@mcp.tool()
def search_postmortems(
    signature: str, limit: int = 5, ctx: Context | None = None
) -> list[ChunkResult]:
    """
    Semantic search over postmortems. Use keywords or signature (e.g. "bus voltage", "telemetry gap").
    Returns matching chunks and doc_id for citations.
    """
    parent_context = extract_w3c_context_from_headers(_extract_headers_from_ctx(ctx))
    tracer = get_tracer("apps.mcp.kb")
    with tracer.start_as_current_span(
        "mcp.kb.search_postmortems", context=parent_context, kind=SpanKind.SERVER
    ) as span:
        span.set_attribute("tool", "search_postmortems")
        if not signature or not signature.strip():
            span.set_attribute("outcome", "empty")
            return []
        try:
            vec = _get_embeddings().embed_query(signature.strip())
            retrieve_k = max(
                int(limit), int(getattr(settings, "kb_reranker_retrieve_k", limit))
            )
            candidates = _search(vec, "postmortem", limit=retrieve_k)
            if getattr(settings, "kb_reranker_enabled", False):
                mode = str(getattr(settings, "kb_reranker_mode", "lexical")).strip()
                ranked = rerank_chunks(signature, list(candidates), mode=mode)
                ranked = ranked[:limit]
                out = [
                    ChunkResult(content=r["content"], doc_id=r["doc_id"])
                    for r in ranked
                ]
                span.set_attribute("outcome", "success" if out else "empty")
                return out
            out = candidates[:limit]
            span.set_attribute("outcome", "success" if out else "empty")
            return out
        except Exception:
            span.set_status(Status(StatusCode.ERROR, "search_postmortems failed"))
            span.set_attribute("outcome", "failure")
            raise


if __name__ == "__main__":
    import uvicorn

    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=8002)
