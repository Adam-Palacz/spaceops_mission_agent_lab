# SpaceOps Mission Agent Lab

Agent for satellite / ground segment anomaly triage: **ingest ? triage ? investigate ? decide ? report**. Automatic action checklists, GitOps PRs to config (S2), and operational reports. Runs on simulated data (telemetry, events, logs); architecture is production-style.

## Docs

| Doc | Description |
|-----|-------------|
| [**roadmap/goals.md**](./roadmap/goals.md) | Goals, assumptions, requirements (F1?F10, NF1?NF9), policy, MoE/MoP, production-ready criteria, audit log schema (§4.6). |
| [**roadmap/01-core-roadmap.md**](./roadmap/01-core-roadmap.md) | Sprints (S1, S2), Phase 4 hardening, task list. |
| [**roadmap/README.md**](./roadmap/README.md) | Execution plan: phases, sprints, task specs. |
| [**docs/README.md**](./docs/README.md) | Index of Mermaid diagrams (pipeline, architecture, state flow, Act flow, repo structure). |
| [**roadmap/01-core/README.md**](./roadmap/01-core/README.md) | Sprint boards and task specs (S1.x, S2.x). |

## Environment

- Copy **.env.example** to **.env** and set `OPENAI_API_KEY` (required for agent). Optional: `POSTGRES_*` if not using defaults.
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

## Testing

```bash
pytest tests/ -v
```

Pre-commit (when configured): `pre-commit run --all-files`. CI runs ruff, mypy, pytest (see S1.13 / S1.14).
