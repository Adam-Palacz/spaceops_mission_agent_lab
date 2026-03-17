# Operator Walkthrough: incident → evidence → policy → approval → PR

This walkthrough is for an operator or reviewer who wants to see how the SpaceOps Agent
handles a real incident end-to-end: from ingest, through the LangGraph pipeline, to OPA
policy checks, human approval, and a GitOps-style PR.

Use together with the diagrams in `docs/workflow/end_to_end_pipeline.mmd` and
`docs/agent/langgraph_state_flow.mmd`.

## 1. Ingest an incident

1. **Ingest telemetry / events** (optional but recommended):
   - `POST /ingest?source=telemetry` with NDJSON from `data/telemetry/` (see README).
2. **Create a run**:
   - `POST /runs` with:
     ```json
     {
       "incident_id": "inc-ops-1",
       "payload": {
         "time_range_start": "2025-02-14T09:00:00Z",
         "time_range_end": "2025-02-14T11:00:00Z"
       }
     }
     ```
   - or via CLI:
     ```bash
     python -m apps.agent.run inc-ops-1 '{"time_range_start":"2025-02-14T09:00:00Z","time_range_end":"2025-02-14T11:00:00Z"}'
     ```

Behind the scenes, this enters the LangGraph pipeline:
**Triage → Investigate → Decide → Act → Report**.

## 2. Evidence gathering (Investigate)

- **Investigate** calls:
  - Telemetry MCP (`query_telemetry`) over HTTP,
  - KB MCP (`search_runbooks`, `search_postmortems`).
- It builds:
  - `hypotheses` — short notes about what might be happening,
  - `citations` — structured references to telemetry / runbooks / postmortems.
- If MCP servers are down, it produces a fallback hypothesis and empty citations instead
  of hanging or crashing (see chaos tests).

You can inspect these fields in the final `report` or by looking at audit log entries for
`query_telemetry`, `search_runbooks`, `search_postmortems`.

## 3. Plan with policy context (Decide)

- **Decide** uses a versioned prompt from `prompts/registry.py` to produce an action plan.
- Each step in `plan` includes:
  - `action` — human-readable description,
  - `safe` — whether it is safe to execute automatically,
  - `action_type` — `create_ticket`, `create_pr`, `change_config`, or `report`,
  - `doc_ids` / `snippet_ids` — citations grounding the step.
- LLM observability logs the triage/decide calls (model, prompt ID/version, tokens).

At this point you have **evidence + a structured plan** for the incident.

## 4. Act: safe vs restricted + OPA policy

When the pipeline reaches **Act**:

- For **safe steps** (`safe=true`):
  - `create_ticket` → Ticketing MCP is called to create or simulate a ticket.
  - `create_pr` → GitOps MCP writes/updates files under `ops-config/` and returns a summary.
- For **restricted steps** (`safe=false`, typically `change_config` / `restart_service`):
  1. Agent calls OPA (`opa_allow`) with incident + step as input.
  2. OPA policy (Rego) decides **allow** or **deny** based on tool/arguments
     (e.g. denies “restart all”).
  3. If **allow**:
     - Agent **does not execute** the change yet,
     - Instead, it creates an approval request in `data/approvals/`.
  4. If **deny** or OPA errors/timeouts:
     - Agent escalates with `reason="policy_deny"`,
     - No approval request is created, no step is executed (fail-closed).

All of these decisions are written to the audit log (`data/audit.ndjson`) with
`actor="agent"`, tool names, outcomes, and error messages.

## 5. Human approval and execution

When a restricted step has been allowed by OPA and turned into an approval request:

1. **List approvals**:
   - `GET /approvals` (with `APPROVAL_API_KEY` in headers) shows pending requests, including
     incident id, step index, and action text.
2. **Approve or reject**:
   - `POST /approvals/{id}/approve` or `.../reject`:
     - Authenticated via `APPROVAL_API_KEY`,
     - Idempotent: a second approve on the same id returns 200 but does not re-execute.
3. **On approve**:
   - For `change_config`, `approval_executor.execute_approved_action` uses GitOps MCP
     to write/update config under `ops-config/` (mock PR),
   - For `restart_service`, it records a no-op “restart requested” outcome.
4. **On reject**:
   - Status is updated to `rejected`; no execution happens.

Each approve/reject becomes an audit log entry with `actor="human"`, the decision, and
timestamps. This closes the **policy + approval** loop.

## 6. Resulting report and follow-up

The final **Report** object returned by `/runs` includes:

- `executive_summary` — including escalation reason when applicable,
- `evidence` and `citation_refs` — summarised hypotheses and references,
- `proposed_actions` — the action texts from the plan,
- `act_results` (when safe actions ran),
- `approval_requests` (for restricted steps awaiting or having completed approval),
- `escalation_packet` when the run escalated,
- `trace_link` — URL to Jaeger for the run’s trace.

Post-incident, you can:

- Use the audit log + Jaeger trace to understand exactly what happened,
- Turn the incident into a postmortem and new eval case (`evals/cases.yaml`),
- Iterate on policy (OPA) or prompts, then re-run evals and, if needed, shadow-testing
  with `python -m evals.shadow_models` before switching models.

