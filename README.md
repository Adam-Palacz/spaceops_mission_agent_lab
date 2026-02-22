# SpaceOps Mission Agent Lab

Agent for satellite / ground segment anomaly triage, automatic action checklists, GitOps PRs to config, and operational reports. Runs on simulated data (telemetry, events, logs); architecture is production-style.

## Docs

- **[goals.md](goals.md)** ? Goals, assumptions, requirements (F1?F10, NF1?NF9), policy, MoE/MoP, production-ready criteria, audit log schema.
- **[project_doc.md](project_doc.md)** ? Concept analysis, workflow, phases, repo structure (PL).
- **[roadmap_F1.md](roadmap_F1.md)** ? Sprints (S1, S2), Phase 4 hardening, tasks.
- **[docs/diagrams.md](docs/diagrams.md)** ? Mermaid diagrams: pipeline, architecture, state flow, Act flow, roadmap, requirements, audit schema, repo structure, MoE/MoP.

## Environment (secure)

- Copy **.env.example** to **.env** and set values (e.g. `OPENAI_API_KEY`). Do not commit `.env` (it is in `.gitignore`).
- All apps load `.env` from repo root via `config.settings`; secrets stay out of shell history.

## Quick start (when implemented)

```bash
# Dependencies (Python 3.12)
pip install -r requirements.txt

# Stack (Postgres, OTel, Jaeger)
docker compose -f infra/docker-compose.yml up -d
# POST /ingest with NDJSON; trigger run; see docs/ and goals.md.
```
