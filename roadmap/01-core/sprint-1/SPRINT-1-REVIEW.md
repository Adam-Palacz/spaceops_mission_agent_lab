# Sprint 1 — Review

**Sprint:** 01-core, Sprint 1 (Full pipeline to Report)  
**Scope:** S1.1–S1.20 (including post-review hardening tasks)  
**Status:** All tasks Done.

---

## 1. Executive summary

Sprint 1 delivered a **complete pipeline** from ingest to report: a single command brings up the stack (Postgres, OTel, Jaeger); the API accepts data and invokes the agent; the agent runs Triage → Investigate → Decide → Report with escalation on lack of evidence/timeouts/limits; audit log and OTel traces are in place; evals and unit tests run in CI. Post-review tasks (S1.15–S1.20) hardened eval scoring, observability/config, audit semantics, and MCP telemetry client behaviour. **Sprint goal achieved.** Act (ticketing, GitOps, OPA, approvals) is intentionally out of scope for S1 and planned for S2.

---

## 2. Sprint goal and assessment

**Goal (from roadmap):**  
*One command runs the stack; ingest → triage → investigate → decide → report works end-to-end with basic evals and OTel traces. No act yet; evidence and escalation path in place.*

| Criterion | Status | Notes |
|-----------|--------|--------|
| Single command brings up stack | ✅ | `docker compose -f infra/docker-compose.yml up -d` + `python -m apps.api.main` |
| Ingest → triage → investigate → decide → report E2E | ✅ | `POST /runs` or `python -m apps.agent.run` |
| Report with trace link | ✅ | `report.trace_link` → Jaeger (when OTel enabled) |
| Escalation path (no evidence / limit / timeout) | ✅ | Escalation packet (F10), reason in report |
| Basic evals in CI | ✅ | 8 cases, `evals/scoring.py`, workflow in ci.yml |
| OTel traces in Jaeger | ✅ | Agent + API instrumented; OTLP export to Collector |
| No Act | ✅ | Plan only in report; execution in S2 |

**Verdict:** Sprint goal **achieved**.

---

## 3. What was done — task by task

### S1.1 — Directory structure
- **Why:** Consistent repo layout for API, agent, MCP, data, KB, evals, infra, docs.
- **What:** Directories `apps/api`, `apps/agent`, `apps/mcp/telemetry_server`, `apps/mcp/kb_server`, `data/`, `kb/runbooks`, `kb/postmortems`, `evals/`, `infra/`, `docs/` (with subdirs workflow, architecture, agent, planning, requirements, data).
- **Where:** Repo-wide; [docs/architecture/repo_structure.mmd](../../docs/architecture/repo_structure.mmd) (if present).

### S1.2 — Docker Compose
- **Why:** Single command for Postgres with pgvector, OTel Collector, Jaeger (goals §4.5).
- **What:** `infra/docker-compose.yml` — services postgres, otel-collector, jaeger; `infra/otel-collector.yaml` (OTLP → Jaeger).
- **How to run:** `docker compose -f infra/docker-compose.yml up -d` from repo root.

### S1.3 — Pinned deps
- **Why:** Reproducible installs (goals §4.5).
- **What:** `requirements.txt` with pinned versions (FastAPI, LangGraph, OTel, MCP, PyYAML, pytest, ruff, mypy, etc.).

### S1.4 — FastAPI: health, ingest, trigger
- **Why:** F1 (Ingest), entry point to the pipeline.
- **What:** `apps/api/main.py` — `GET /health`, `POST /ingest?source=telemetry|events|ground_logs` (NDJSON, validation, write to `data/{source}/`), `POST /runs` (invoke agent).
- **Tests:** `tests/test_api.py` (health 200, ingest valid/invalid, persistence, sources).

### S1.5 — NDJSON fixtures
- **Why:** Reproducible data (goals §4.5).
- **What:** Fixtures in `data/telemetry/`, `data/events/`, `data/ground_logs/` (a few records each).
- **Tests:** `tests/test_fixtures.py` (NDJSON schema when files exist).

### S1.6 — MCP Telemetry + KB (RAG)
- **Why:** F3 (Investigate) — agent queries telemetry and KB.
- **What:**  
  - MCP Telemetry: `apps/mcp/telemetry_server/` — `query_telemetry(time_range, channels)`; port 8001.  
  - MCP KB: `apps/mcp/kb_server/` — `search_runbooks`, `search_postmortems` (pgvector); `index_kb.py`; port 8002.  
  - Runbooks and postmortems in `kb/runbooks/`, `kb/postmortems/`; vector schema in `infra/sql/001_kb_vector.sql`.

### S1.7 — LangGraph: Triage → Investigate → Decide → Report
- **Why:** Agent core (F2, F3, F4, F7); NF5a (citation grounding).
- **What:**  
  - State: `apps/agent/state.py` (AgentState, Citation, PlanStep, EscalationPacket).  
  - Nodes: `apps/agent/nodes.py` — triage (LLM, subsystem + risk), investigate (MCP Telemetry + KB, hypotheses + citations), decide (plan with doc_id/snippet_id), report (summary, evidence, actions, rollback, trace_link).  
  - Graph: `apps/agent/graph.py` — triage → investigate → check_escalation → decide or build_report → END.  
  - MCP client: `apps/agent/mcp_client.py` (sync wrappers over async MCP).  
  - Entry: `POST /runs` or `python -m apps.agent.run`.

### S1.8 — Escalation path (F10)
- **Why:** Explicit handoff to human on low confidence / no evidence / conflict.
- **What:** In `nodes.py`: `_should_escalate`, `check_escalation` (no_evidence, high_risk_no_evidence, conflicting_signals); conditional edge to report with escalation_packet; report with `[ESCALATION]` and packet.
- **Tests:** `tests/test_agent_pipeline.py` (escalation conditions, packet in report).

### S1.9 — Audit log (append-only)
- **Why:** NF2, goals §4.6 — immutable record of actions.
- **What:** `apps/agent/audit_log.py` — schema (timestamp, trace_id, incident_id, actor, tool, args_hash, decision, policy_result, outcome); write to NDJSON (default `data/audit.ndjson`); integration in investigate (after each MCP call).
- **Config:** `config.audit_log_path`.  
- **Tests:** `tests/test_audit_log.py` (schema, args_hash, append-only, entries after run).

### S1.10 — OTel + Jaeger
- **Why:** NF2, §4.5 — traces and structured logging.
- **What:** `apps/telemetry.py` — TracerProvider, OTLP export, get_tracer, get_current_trace_id_hex, JsonTraceFormatter (logs with trace_id); instrumentation in agent (span per node + per MCP call) and FastAPI; report `trace_link` with actual trace_id (hex) when OTel enabled.
- **Config:** `config.otel_exporter_otlp_endpoint` (empty = disabled).  
- **Tests:** `tests/test_otel_jaeger.py` (URL in report, trace_id, logs with trace_id).

### S1.11 — Evals
- **Why:** NF4, MoE1–MoE4 — triage, citations, escalation in CI.
- **What:** `evals/cases.yaml` (8 cases: triage top-1/top-2, citation, must-escalate), `evals/scoring.py` (run agent, compare to expectations, exit 0/1); determinism (temperature=0).
- **CI:** Evals job in `ci.yml`; requires `OPENAI_API_KEY` in secrets.  
- **Tests:** `tests/test_evals.py` (case format, scoring runs).

### S1.12 — Limits and timeouts (NF6)
- **Why:** Cost and time under control; no “hung” operations.
- **What:** In `config`: agent_run_timeout_seconds, agent_llm_call_timeout_seconds, agent_token_budget_per_run, agent_max_llm_calls_per_run. In agent: run-level timeout (ThreadPoolExecutor), token counting in triage/decide, LLM call limit; on exceed — escalation (run_timeout, token_limit, rate_limit, llm_timeout).
- **Tests:** `tests/test_limits_timeouts.py` (timeout → escalation, token limit → escalation, rate limit → escalation, normal run without false escalation).

### S1.13 — pre-commit, CI, README
- **Why:** Quality and documentation (NF7).
- **What:** `.pre-commit-config.yaml` (ruff, mypy); `.github/workflows/ci.yml` (lint: ruff + mypy, test: pytest tests/, evals: evals.scoring); README with Quick start, ingest, run agent, tests, evals, pre-commit, env vars.

### S1.14 — Unit tests
- **Why:** Regression and behaviour documentation.
- **What:** `tests/conftest.py` (api_client with DATA_DIR/REPO_ROOT patch); `tests/test_api.py` (health, ingest valid/invalid/persistence/source); `tests/test_fixtures.py` (NDJSON fixture schema). Existing: test_audit_log, test_agent_pipeline, test_evals, test_limits_timeouts, test_otel_jaeger, test_mcp_telemetry.

### S1.15 — Evals hardening (top_k, citation vs escalation)
- **Why:** Make evals truly gate quality for triage and citations; prevent citation-required cases from “passing via escalation”.
- **What:** `evals/scoring.py` now respects `expected_subsystem_top_k` (triage must land within the first k expected subsystems) and treats `require_citations: true` + non-mandatory escalation as a failure (escalation is not allowed to satisfy citation-present cases); full evals run remains deterministic and CI-stable.

### S1.16 — .env.example and single-command observability
- **Why:** Ensure that the “single-command” experience actually produces traces in Jaeger and that all important env vars are discoverable.
- **What:** `.env.example` extended with OTel and agent limit/timeouts (`OTEL_EXPORTER_OTLP_ENDPOINT`, `AGENT_*`); with Compose up + copying `.env.example` and setting `OPENAI_API_KEY` and OTLP endpoint, running one `/runs` produces traces visible in Jaeger; README/.env comments clarify how to enable tracing.

### S1.17 — Config: optional Postgres for no-DB modes
- **Why:** Allow running the core API/agent and Telemetry MCP without requiring Postgres when KB/RAG is not in use.
- **What:** `config.Settings.postgres_password` made optional for core apps; `postgres_dsn` is only required/used by KB server/indexer, which now fail fast with a clear error when DB config is missing; `.env.example` documents that Postgres vars are optional unless using KB/RAG.

### S1.18 — Audit log: outcome failure vs empty, error details
- **Why:** Distinguish “tool returned no results” from “tool failed” in audits, for better debugging and compliance.
- **What:** Audit entries for MCP calls now set `outcome` to `success`, `empty`, or `failure`, and on failures can capture a short, safe error indicator (e.g. `error_message`/hash); `audit_log.append_entry` schema extended accordingly and tests updated to cover the new semantics.

### S1.19 — (Optional) Code readability / maintainability pass
- **Why:** Reduce cognitive load for future work on the agent, MCP integration, and evals without changing behaviour.
- **What:** Light readability pass on `apps/agent/nodes.py`, `apps/agent/mcp_client.py`, `evals/scoring.py`, and related config: split dense one-liners, name intermediate values, and clarify non-obvious conditionals; tests and evals continue to pass unchanged.

### S1.20 — MCP Telemetry client integration (citation-present)
- **Why:** Fix the Telemetry MCP client so that when telemetry evidence exists, the agent uses it for grounded citations instead of escalating.
- **What:** `apps/agent/mcp_client.py::call_telemetry` (and related KB MCP helpers) updated to correctly decode FastMCP/StreamableHTTP tool results (`structuredContent` and `content` blocks), so that for the `citation-present` window and `channels: ["bus_voltage"]` the client returns real telemetry samples; full eval run (`python -m evals.scoring`) now passes all 8 cases with `citation-present` succeeding via citations rather than escalation.

---

## 4. Project state after S1

### How to run (single-command idea)
1. **Environment:** `pip install -r requirements.txt`, `.env` with `OPENAI_API_KEY` (and optionally `POSTGRES_*`).
2. **Stack:** `docker compose -f infra/docker-compose.yml up -d` (Postgres, OTel Collector, Jaeger).
3. **API:** `python -m apps.api.main` → http://localhost:8000 (health, ingest, runs).
4. **Optional (richer Investigate):** MCP Telemetry (8001), MCP KB (8002), `python -m apps.mcp.kb_server.index_kb`.

### What works
- **Ingest:** POST /ingest with NDJSON → validation and write to `data/{source}/`.
- **Run:** POST /runs with incident_id + payload → pipeline Triage → Investigate → check_escalation → Decide or Report → response with report (including escalation_packet on escalation).
- **Report:** executive_summary, evidence, citation_refs, proposed_actions, rollback, trace_link (Jaeger); on escalation — handoff and escalation_packet.
- **Audit:** Each MCP call in investigate writes an entry to the audit log (NDJSON).
- **Traces:** With OTel endpoint set, traces go to Jaeger (one trace per run, spans per node and per tool).
- **Evals:** `python -m evals.scoring` — 8 cases; CI runs evals (with OPENAI_API_KEY).
- **Tests:** `pytest tests/ -v`; CI: ruff, mypy, pytest, evals.

### Where things live (map)
| Area | Paths |
|------|-------|
| API | `apps/api/main.py` |
| Agent (graph, state, nodes) | `apps/agent/graph.py`, `state.py`, `nodes.py`, `mcp_client.py`, `audit_log.py`, `run.py` |
| Telemetry | `apps/telemetry.py` (OTel); `apps/mcp/telemetry_server/` |
| KB / RAG | `apps/mcp/kb_server/`, `kb/runbooks/`, `kb/postmortems/`, `infra/sql/001_kb_vector.sql` |
| Config | `config.py`, `.env.example` |
| Evals | `evals/cases.yaml`, `evals/scoring.py` |
| Infra | `infra/docker-compose.yml`, `infra/otel-collector.yaml` |
| Tests | `tests/test_*.py`, `tests/conftest.py` |
| Docs | `docs/README.md` (diagram index), `roadmap/goals.md`, `roadmap/01-core-roadmap.md` |

---

## 5. Requirements coverage (goals) in S1

| ID | Requirement | S1 | Notes |
|----|-------------|-----|--------|
| F1 | Ingest (webhook/CLI, NDJSON) | ✅ | POST /ingest, write to data/ |
| F2 | Triage (subsystem, risk) | ✅ | Triage node |
| F3 | Investigate (telemetry, KB) | ✅ | MCP Telemetry + KB, hypotheses + citations |
| F4 | Decide (plan, safe vs restricted) | ✅ | Plan with citation; safe/restricted in S2 (Act) |
| F7 | Report (brief, evidence, trace link) | ✅ | Report node |
| F10 | Escalate-to-human (packet) | ✅ | check_escalation, escalation_packet |
| NF1 | No shell/exec, only MCP | ✅ | MCP only in agent |
| NF2 | Traces + audit log | ✅ | OTel + audit_log.ndjson |
| NF4 | Evals in CI | ✅ | evals in ci.yml |
| NF5a | Citation grounding | ✅ | Decide requires doc_id/snippet_id in steps |
| NF6 | Token/rate limits, timeouts | ✅ | S1.12 |
| NF7 | Documentation | ✅ | README, docs/README, evals/README, roadmap |

F5, F6, F8 (Act, OPA, Approval API) and NF3, NF8, NF9 are planned for **S2**.

---

## 6. Definition of done (sprint) — checklist

- [x] Single command brings up stack; ingest → report runs; report includes trace link.
- [x] Escalation packet produced when conditions are met.
- [x] Audit log has correct schema; append-only.
- [x] Evals run in CI; triage, citation, escalation covered.
- [x] Traces visible in Jaeger (when OTel endpoint set).
- [x] Unit tests in tests/ for API, audit log, and critical paths; pytest in CI.

---

## 7. What's next — Sprint 2

S2 introduces **Act**: safe (ticket, GitOps PR) and restricted (OPA + approval API). Key tasks: ops-config (S2.1), MCP Ticketing + GitOps (S2.2), Decide→Act + OPA fail-closed (S2.3–S2.6), Approval API (S2.5, S2.7), injection suite (S2.8), metrics and dashboard (S2.9).  
Details: [../sprint-2/README.md](../sprint-2/README.md), [../../01-core-roadmap.md](../../01-core-roadmap.md).

---

## 8. Suggestions for future reviews

- **Metrics:** Add to review: test count (e.g. `pytest tests/ --co -q`), evals case count, optionally full `pytest tests/` and `evals.scoring` duration (to track regression).
- **Risks / open items:** e.g. “Evals in CI depend on OPENAI_API_KEY in secrets”; “MCP servers not in docker-compose (BL-003 in backlog)”.
- **Retro (optional):** Short section: what went well, what was hard, one thing to improve in S2.

---

*Sprint 1 review — state at sprint close. Update when scope changes or S1 is reopened.*
