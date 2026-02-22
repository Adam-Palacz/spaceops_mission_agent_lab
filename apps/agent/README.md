# SpaceOps Agent — LangGraph pipeline (S1.7)

Pipeline: **Triage** → **Investigate** → **Decide** → **Report** (no Act node yet). LLM calls use the OpenAI Chat Completions API via httpx.

## Nodes

- **Triage** — Classify subsystem (ADCS/Power/Thermal/Comms/Payload/Ground) and risk; persist incident to `data/incidents/`.
- **Investigate** — Call Telemetry MCP (`query_telemetry`) and KB MCP (`search_runbooks`, `search_postmortems`); attach hypotheses and citations. If MCP servers are down, returns empty hypotheses/citations and continues.
- **Decide** — LLM produces an action plan; each step must reference at least one `doc_id` or `snippet_id` (NF5a citation grounding).
- **Report** — Executive summary, evidence, proposed actions, rollback note, trace link (Jaeger UI URL placeholder).

## Prerequisites

- **.env** with `OPENAI_API_KEY` (required for Triage and Decide).
- **Optional:** MCP Telemetry at `TELEMETRY_MCP_URL` (default `http://localhost:8001/mcp`), MCP KB at `KB_MCP_URL` (default `http://localhost:8002/mcp`) with KB indexed — for richer Investigate results.

## Run from CLI

From repo root:

```bash
python -m apps.agent.run inc-1 '{"time_range_start":"2025-02-14T09:00:00Z","time_range_end":"2025-02-14T11:00:00Z"}'
```

Payload can include `time_range_start`, `time_range_end`, `channels` (list), or any JSON; Triage/Decide use it for context.

## Invoke from API

`POST http://localhost:8000/runs` with body:

```json
{"incident_id": "inc-1", "payload": {"time_range_start": "2025-02-14T09:00:00Z", "time_range_end": "2025-02-14T11:00:00Z"}}
```

Returns **200** with `{"status": "completed", "incident_id": "...", "report": {...}}`. On failure returns 500 and writes the error to `data/incidents/run_*.json`.
