# Knowledge base — runbooks and postmortems

Used by the agent (via MCP KB server) for RAG: semantic search over runbooks and postmortems (pgvector).

## Layout

| Folder | Purpose |
|--------|--------|
| **runbooks/** | Operational runbooks (e.g. power bus voltage, thermal, telemetry gap). Markdown. |
| **postmortems/** | Post-incident write-ups; signature and tags for search. Markdown. |
| **policies/** | Policy snippets (OPA, compliance); referenced by agent/approval flow. |

## Indexing

The MCP KB server reads from **pgvector** (table `kb_chunks`), not directly from these files. To populate/update:

1. Start Postgres (with pgvector): `docker compose -f infra/docker-compose.yml up -d`
2. Run index script: `OPENAI_API_KEY=... python -m apps.mcp.kb_server.index_kb`

See `apps/mcp/kb_server/README.md`.

## Fixtures (S1.6)

- **Runbooks:** 3 samples — power bus voltage anomaly, thermal plate temperature high, telemetry gap.
- **Postmortems:** 1 sample — bus voltage below nominal (false positive, link glitch).
