# BL-003 — MCP servers in Docker Compose

**Backlog item** — use this spec to create a sprint task (e.g. S2.x or P4.x) when you schedule this work. The backlog has no statuses.

| Field | Value |
|-------|--------|
| **Backlog ID** | BL-003 |
| **Source** | MCP Telemetry and KB servers (S1.6) today run as separate processes; containerizing them aligns with S1.2 stack and single-command run (goals.md §4.5). |

---

## Description

**Objective:** Add MCP Telemetry server and MCP KB server as services in `infra/docker-compose.yml` so that `docker compose up -d` brings up the full stack (Postgres, OTel, Jaeger, Telemetry MCP, KB MCP). Optionally include the API and/or agent in the same Compose for a one-command dev/production-style run.

MCP servers are long-running; running them in containers matches the rest of the stack and avoids manually starting them in separate terminals.

---

## Requirements

- [ ] Telemetry MCP service in docker-compose: listens on 8001, serves `query_telemetry`; reads from mounted or shared `data/telemetry` (or document that data is injected at deploy time).
- [ ] KB MCP service in docker-compose: listens on 8002, depends on Postgres; has access to `OPENAI_API_KEY` (env or secrets) for embeddings; KB index step (e.g. `index_kb`) can be init container or documented manual step after first start.
- [ ] Agent (and API if in Compose) can reach MCP servers via service names (e.g. `http://telemetry:8001/mcp`, `http://kb:8002/mcp`); config (e.g. `TELEMETRY_MCP_URL`, `KB_MCP_URL`) supports override for local vs Compose.
- [ ] Document in README or infra/ how to run the full stack and optional indexing of KB after Postgres is up.

---

## Checklist

- [ ] Add `telemetry` (and optionally `kb`) service(s) to `infra/docker-compose.yml`; use Python image and mount repo code or build from Dockerfile in `apps/mcp/`.
- [ ] KB service: env `OPENAI_API_KEY` (from env_file or placeholder); depends_on Postgres; document running `index_kb` once (e.g. exec into container or init script).
- [ ] Telemetry service: mount `data/telemetry` or equivalent so fixture/ingest data is visible.
- [ ] Update `config.py` or `.env.example` so that when running inside Compose, agent/API use service names for MCP URLs (or document host vs container networking).
- [ ] README or infra README: one-command run with `docker compose up -d`; optional: API + agent as services; how to run index_kb and trigger a run.

---

## Test requirements

- `docker compose -f infra/docker-compose.yml up -d` starts all services including MCP; Telemetry MCP responds at `http://localhost:8001/mcp` (or service name from another container).
- KB MCP responds at 8002 after Postgres is healthy; after indexing, `search_runbooks` returns at least one chunk when called via MCP client.
- Agent (run from host or from container) can call both MCPs when pointed at container URLs/ports.
