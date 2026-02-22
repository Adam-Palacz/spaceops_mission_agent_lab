# SpaceOps Mission Agent Lab

Agent for satellite / ground segment anomaly triage: ingest ? triage ? investigate ? decide ? report. Automatic action checklists, GitOps PRs to config (later), and operational reports. Runs on simulated data (telemetry, events, logs); architecture is production-style.

## Docs

- **[goals.md](goals.md)** ? Goals, assumptions, requirements (F1?F10, NF1?NF9), policy, MoE/MoP, production-ready criteria, audit log schema.
- **[project_doc.md](project_doc.md)** ? Concept analysis, workflow, phases, repo structure.
- **[roadmap_F1.md](roadmap_F1.md)** ? Sprints (S1, S2), Phase 4 hardening, tasks.
- **[docs/diagrams.md](docs/diagrams.md)** ? Mermaid diagrams: pipeline, architecture, state flow, Act flow, repo structure, MoE/MoP.

## Environment (secure)

- Copy **.env.example** to **.env** and set values (e.g. `OPENAI_API_KEY`, optional `POSTGRES_*`). Do not commit `.env` (it is in `.gitignore`).
- All apps load `.env` from repo root via `config.settings`; secrets stay out of shell history.

## Quick start

```bash
# Dependencies (Python 3.12)
pip install -r requirements.txt

# Stack (Postgres+pgvector, OTel, Jaeger)
docker compose -f infra/docker-compose.yml up -d

# API (health, ingest, trigger run)
python -m apps.api.main
# ? http://localhost:8000  |  GET /health  |  POST /ingest?source=telemetry  |  POST /runs
```

**Ingest fixture:**  
`curl -X POST "http://localhost:8000/ingest?source=telemetry" -H "Content-Type: application/x-ndjson" --data-binary @data/telemetry/telemetry.ndjson`

**Run agent:**  
`POST /runs` with `{"incident_id": "inc-1", "payload": {"time_range_start": "2025-02-14T09:00:00Z", "time_range_end": "2025-02-14T11:00:00Z"}}` ? returns report. Or CLI: `python -m apps.agent.run inc-1 '{"time_range_start":"2025-02-14T09:00:00Z","time_range_end":"2025-02-14T11:00:00Z"}'`

**Optional (for Investigate node):** MCP Telemetry on 8001, MCP KB on 8002; index KB with `python -m apps.mcp.kb_server.index_kb`. See [apps/agent/README.md](apps/agent/README.md) and [apps/mcp/*/README.md](apps/mcp/).
