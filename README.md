# SpaceOps Mission Agent Lab

Agent for satellite / ground segment anomaly triage: **ingest ? triage ? investigate ? decide ? report**. Automatic action checklists, GitOps PRs to config (S2), and operational reports. Runs on simulated data (telemetry, events, logs); architecture is production-style.

## Docs

| Doc | Description |
|-----|-------------|
| [**roadmap/goals.md**](./roadmap/goals.md) | Goals, assumptions, requirements (F1?F10, NF1?NF9), policy, MoE/MoP, production-ready criteria, audit log schema (?4.6). |
| [**roadmap/base-roadmap.md**](./roadmap/base-roadmap.md) | Sprints (S1, S2, S3), Phase 4 hardening, tech-debt sprint, task list. |
| [**roadmap/01-foundation-mvp.md**](./roadmap/01-foundation-mvp.md) | Foundation/MVP storyline: core agent, MCPs, evals, and escalation. |
| [**roadmap/02-production-scale.md**](./roadmap/02-production-scale.md) | Post-MVP productionisation: streaming, safety gates, LLM backends, K8s/cloud. |
| [**roadmap/post-mvp.md**](./roadmap/post-mvp.md) | Long-term roadmap: phases, ideas, and production-grade criteria. |
| [**roadmap/03-next-gen-autonomy.md**](./roadmap/03-next-gen-autonomy.md) | Next-gen autonomy (L3/L4): Flight Director multi-agent pattern, collaborative planning, compliance gateway, edge SLMs, GraphRAG. |
| [**roadmap/README.md**](./roadmap/README.md) | Execution plan: phases, sprints, task specs. |
| [**docs/README.md**](./docs/README.md) | Index of Mermaid diagrams (pipeline, architecture, state flow, Act flow, repo structure). |
| [**roadmap/01-core/README.md**](./roadmap/01-core/README.md) | Sprint boards and task specs (S1.x, S2.x, S3.x). |

## Environment

- Copy **.env.example** to **.env** and set `OPENAI_API_KEY` (required for agent). Optional: `POSTGRES_*` if not using defaults.
- **Limits and timeouts (S1.12, NF6):** `AGENT_RUN_TIMEOUT_SECONDS` (default 120; 0 = no limit), `AGENT_LLM_CALL_TIMEOUT_SECONDS` (default 30), `AGENT_TOKEN_BUDGET_PER_RUN` (default 50000; 0 = no limit), `AGENT_MAX_LLM_CALLS_PER_RUN` (default 10; 0 = no limit). When exceeded, run escalates to human.
- **OTel traces (S1.10):** to export traces to the local collector/Jaeger from apps, set `OTEL_EXPORTER_OTLP_ENDPOINT` (e.g. `http://localhost:4317`, matching `infra/docker-compose.yml`).
- **MCP + GitOps (S2):** MCP URLs can be overridden via `TELEMETRY_MCP_URL`, `KB_MCP_URL`, `TICKET_MCP_URL`, `GITOPS_MCP_URL` (see `.env.example`). For GitOps PR creation, set `GITHUB_TOKEN`, `GITHUB_REPO`, `GITHUB_REPO_BASE_BRANCH`.
- **OPA policy (S2.4):** OPA endpoint and timeout are configurable via `OPA_URL` and `OPA_TIMEOUT_SECONDS`; by default OPA runs as `opa` service in `infra/docker-compose.yml`.
- Do not commit `.env` (in `.gitignore`). All apps load it from repo root via `config.settings`.

## Quick start

```bash
# Dependencies (Python 3.12)
pip install -r requirements.txt

# Stack (Postgres+pgvector, OTel, Jaeger)
docker compose -f infra/docker-compose.yml up -d

# API
python -m apps.api.main
# ? http://localhost:8000  |  GET /health  |  POST /ingest  |  POST /runs
```

**Ingest fixture:**  
`curl -X POST "http://localhost:8000/ingest?source=telemetry" -H "Content-Type: application/x-ndjson" --data-binary @data/telemetry/telemetry.ndjson`

**Run agent:**  
`POST /runs` with body `{"incident_id": "inc-1", "payload": {"time_range_start": "2025-02-14T09:00:00Z", "time_range_end": "2025-02-14T11:00:00Z"}}` ? returns report. Or CLI:  
`python -m apps.agent.run inc-1 '{"time_range_start":"2025-02-14T09:00:00Z","time_range_end":"2025-02-14T11:00:00Z"}'`

**Optional (richer Investigate):** Run MCP Telemetry (port 8001) and MCP KB (8002); index KB: `python -m apps.mcp.kb_server.index_kb`. See [apps/agent/README.md](apps/agent/README.md), [apps/mcp/](apps/mcp/).

**GitOps / ops-config (S2):** Config PRs from the agent target the [ops-config/](ops-config/) subtree at repo root. Default branch: `main`; path for MCP: `ops-config/` (local) or the separate repo URL if split. See [ops-config/README.md](ops-config/README.md). To exercise GitOps PR flow locally, run the GitOps MCP server (`python -m apps.mcp.gitops_server.main`) and use `scripts/test_gitops_pr.py` (requires `GITHUB_TOKEN` / `GITHUB_REPO`).

## Testing

```bash
pytest tests/ -v
```

## Formatting

```bash
# Apply standard formatting to Python modules (ruff format)
python -m ruff format .
```

**Evals (S1.11):** `python -m evals.scoring` (requires `OPENAI_API_KEY`). See [evals/README.md](evals/README.md).

**Pre-commit:** Install hooks with `pip install pre-commit && pre-commit install`. Run manually: `pre-commit run --all-files` (ruff, ruff-format, mypy). CI runs ruff, mypy, pytest, and evals on push/PR (S1.13).

## Code style (agents, MCP, evals)

- Prefer one statement per line for control flow (no compressed one-liners with multiple `if`/`and`/`or` branches).
- Name intermediate values when they clarify intent (e.g. `allowed_subsystems`, `telemetry_outcome`) instead of deeply nested expressions.
- Keep evals and agent logic readable first; micro-optimizations are secondary to clarity, especially around escalation, limits, and audit logging.
