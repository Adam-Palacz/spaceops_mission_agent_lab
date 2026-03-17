# SpaceOps Agent — LangGraph pipeline (S1.7–S2.x)

Pipeline: **Triage** → **Investigate** → **Decide** → **Act** → **Report**. LLM calls use the OpenAI Chat Completions API via `httpx`; restricted actions are guarded by OPA and an approval API.

## Nodes

- **Triage** — Classify subsystem (ADCS/Power/Thermal/Comms/Payload/Ground) and risk; persist incident to `data/incidents/`.
- **Investigate** — Call Telemetry MCP (`query_telemetry`) and KB MCP (`search_runbooks`, `search_postmortems`); attach hypotheses and citations. If MCP servers are down, returns fallback hypotheses and continues.
- **Decide** — LLM produces a citation-grounded action plan; each step includes `safe` and `action_type` (`create_ticket`, `create_pr`, `change_config`, `report`) and must reference at least one `doc_id` or `snippet_id` (NF5a).
- **Act** — Executes **safe** steps immediately via Ticketing/GitOps MCP; for **restricted** steps (`safe=false`), calls OPA (`opa_allow`) and, on allow, creates approval requests instead of executing. On deny/error/timeout → **fail-closed** escalation with `reason="policy_deny"`, no execution.
- **Report** — Executive summary, evidence, citation refs, proposed actions, rollback note, trace link to Jaeger, and (when escalated) the escalation packet from Decide/Act.

## Prerequisites

- **.env** with `OPENAI_API_KEY` (required for Triage and Decide).
- **Optional but recommended for full flow:**
  - MCP Telemetry at `TELEMETRY_MCP_URL` and MCP KB at `KB_MCP_URL` — for richer Investigate results.
  - OPA server on `OPA_URL` (default from `config.py`) with `infra/opa/agent_policy.rego` loaded.
  - Approval API key (`APPROVAL_API_KEY`) for `/approvals` endpoints.

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
