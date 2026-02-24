"""
SpaceOps Mission Agent Lab — MCP KB Server
Tools: search_runbooks(query), search_postmortems(signature) — RAG over pgvector.
Requires: Postgres with kb_chunks populated (run index_kb.py); set OPENAI_API_KEY in .env.
"""
from __future__ import annotations

from typing import TypedDict

from langchain_openai import OpenAIEmbeddings
from mcp.server.fastmcp import FastMCP
import psycopg2
from pgvector.psycopg2 import register_vector

from config import settings

EMBEDDING_DIM = 1536


def get_connection():
    """
    Return a Postgres connection for KB RAG.

    S1.17: Fail fast with a clear error if Postgres is not configured.
    Core app (API/agent without KB) should not require POSTGRES_PASSWORD, but KB server does.
    """
    if not settings.database_url and not getattr(settings, "postgres_password", "").strip():
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
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT content, doc_id
            FROM kb_chunks
            WHERE doc_type = %s
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (doc_type, embedding, limit),
        )
        rows = cur.fetchall()
    conn.close()
    return [ChunkResult(content=r[0], doc_id=r[1]) for r in rows]


mcp = FastMCP("SpaceOps KB", json_response=True)
_embeddings = None


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required; set it in .env or environment.")
        _embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.openai_api_key,
        )
    return _embeddings


@mcp.tool()
def search_runbooks(query: str, limit: int = 5) -> list[ChunkResult]:
    """
    Semantic search over runbooks. Returns matching text chunks and their doc_id (filename) for citations.
    Use for investigating anomalies: e.g. "power bus voltage", "thermal temperature high".
    """
    if not query or not query.strip():
        return []
    vec = _get_embeddings().embed_query(query.strip())
    return _search(vec, "runbook", limit=limit)


@mcp.tool()
def search_postmortems(signature: str, limit: int = 5) -> list[ChunkResult]:
    """
    Semantic search over postmortems. Use keywords or signature (e.g. "bus voltage", "telemetry gap").
    Returns matching chunks and doc_id for citations.
    """
    if not signature or not signature.strip():
        return []
    vec = _get_embeddings().embed_query(signature.strip())
    return _search(vec, "postmortem", limit=limit)


if __name__ == "__main__":
    import uvicorn
    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=8002)
