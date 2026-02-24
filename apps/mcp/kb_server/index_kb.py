"""
SpaceOps KB — embed runbooks and postmortems into pgvector.
Run from repo root: python -m apps.mcp.kb_server.index_kb
Requires: .env with OPENAI_API_KEY and Postgres (POSTGRES_* or DATABASE_URL). Schema: infra/sql/001_kb_vector.sql.
"""

from __future__ import annotations

from pathlib import Path

import psycopg2
from langchain_openai import OpenAIEmbeddings
from pgvector.psycopg2 import register_vector

from config import settings

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
KB_RUNBOOKS = REPO_ROOT / "kb" / "runbooks"
KB_POSTMORTEMS = REPO_ROOT / "kb" / "postmortems"
EMBEDDING_DIM = 1536


def get_connection():
    """
    Return a Postgres connection for KB indexing.

    S1.17: Fail fast with a clear error if Postgres is not configured.
    Core app (API/agent without KB) should not require POSTGRES_PASSWORD, but index_kb does.
    """
    if (
        not settings.database_url
        and not getattr(settings, "postgres_password", "").strip()
    ):
        raise SystemExit(
            "Postgres is required to index KB chunks. "
            "Set DATABASE_URL or POSTGRES_PASSWORD/POSTGRES_* in the environment or .env."
        )
    return psycopg2.connect(settings.postgres_dsn)


def ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS kb_chunks (
              id BIGSERIAL PRIMARY KEY,
              doc_id TEXT NOT NULL,
              doc_type TEXT NOT NULL CHECK (doc_type IN ('runbook', 'postmortem')),
              content TEXT NOT NULL,
              embedding vector(1536) NOT NULL,
              created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS kb_chunks_doc_type ON kb_chunks(doc_type);"
        )
    conn.commit()


def chunk_text(text: str, max_chars: int = 600, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks by size; try to break at newlines."""
    chunks: list[str] = []
    start = 0
    text = text.strip()
    while start < len(text):
        end = start + max_chars
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        # break at last newline in window
        segment = text[start:end]
        last_nl = segment.rfind("\n")
        if last_nl > max_chars // 2:
            end = start + last_nl + 1
        chunks.append(text[start:end].strip())
        start = end - overlap
    return [c for c in chunks if c]


def load_docs() -> list[tuple[str, str, str]]:
    """Yield (doc_id, doc_type, content) for each file."""
    out: list[tuple[str, str, str]] = []
    for folder, doc_type in [(KB_RUNBOOKS, "runbook"), (KB_POSTMORTEMS, "postmortem")]:
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            doc_id = path.name
            out.append((doc_id, doc_type, text))
    return out


def main() -> None:
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is required for embedding; set it in .env")
    conn = get_connection()
    register_vector(conn)
    ensure_schema(conn)

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key,
    )
    docs = load_docs()
    if not docs:
        print("No .md files in kb/runbooks or kb/postmortems.")
        return

    # Clear existing so re-run is idempotent replace
    with conn.cursor() as cur:
        cur.execute("DELETE FROM kb_chunks;")
    conn.commit()

    inserted = 0
    with conn.cursor() as cur:
        for doc_id, doc_type, text in docs:
            for chunk in chunk_text(text):
                vec = embeddings.embed_query(chunk)
                cur.execute(
                    "INSERT INTO kb_chunks (doc_id, doc_type, content, embedding) VALUES (%s, %s, %s, %s)",
                    (doc_id, doc_type, chunk, vec),
                )
                inserted += 1
    conn.commit()
    conn.close()
    print(f"Indexed {inserted} chunks from {len(docs)} documents.")


if __name__ == "__main__":
    main()
