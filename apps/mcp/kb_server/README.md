# MCP KB Server

Exposes **search_runbooks** and **search_postmortems** over MCP (Streamable HTTP). RAG over pgvector (runbooks and postmortems from `kb/`).

## Tools

- **search_runbooks(query, limit?)** — Semantic search over runbooks; returns chunks + doc_id (citations).
- **search_postmortems(signature, limit?)** — Semantic search over postmortems; returns chunks + doc_id.

## Prerequisites

1. Postgres with pgvector (e.g. `docker compose -f infra/docker-compose.yml up -d`).
2. Schema: run `infra/sql/001_kb_vector.sql` or run index script once (it creates the table).
3. Index KB: `OPENAI_API_KEY=sk-... python -m apps.mcp.kb_server.index_kb` (from repo root).
4. Env: `OPENAI_API_KEY` (for embedding queries at runtime).

## Run

From repo root:

```bash
set OPENAI_API_KEY=sk-...
python -m apps.mcp.kb_server.main
```

Server: `http://0.0.0.0:8002/mcp`.

## Re-index

After adding or editing files in `kb/runbooks/` or `kb/postmortems/`:

```bash
python -m apps.mcp.kb_server.index_kb
```

(Re-run replaces all chunks in `kb_chunks`.)
