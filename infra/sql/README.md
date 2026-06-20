# SQL migrations / one-off scripts

Postgres bootstrap SQL for local and stage stacks (pgvector extension, KB chunks table, etc.).

## 001_kb_vector.sql

Creates the `vector` extension and the `kb_chunks` table for RAG (runbooks and postmortems).
**Run once** after Postgres starts.

### From the repo root

**Option A - through the container (no host `psql` required):**

```bash
docker exec -i spaceops-postgres psql -U spaceops -d spaceops < infra/sql/001_kb_vector.sql
```

**Option B - from the host (when `psql` is installed):**

```bash
# Password from .env (POSTGRES_PASSWORD)
psql -h localhost -p 5432 -U spaceops -d spaceops -f infra/sql/001_kb_vector.sql
```

If `.env` uses different `POSTGRES_USER`, `POSTGRES_PASSWORD`, or `POSTGRES_DB` values, use those
values in the commands above.

Index the KB: `python -m apps.mcp.kb_server.index_kb` (requires `.env` with `OPENAI_API_KEY` and
running Postgres).

## 002_llm_usage_ledger.sql

Creates **`llm_usage_ledger`** for `LLM_BUDGET_MODE=postgres` (PS7.6 shared UTC-day token cap).
**Run once** after Postgres starts (same `docker exec` / `psql -f` pattern as above).
