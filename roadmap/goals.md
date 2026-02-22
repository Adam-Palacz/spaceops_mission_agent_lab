# SpaceOps Mission Agent Lab — Goals, Assumptions & Requirements

## 1. Project goals

- **Primary:** Build an advanced, production-style system for **anomaly triage** in satellite and ground segment operations, combining AI (agent, RAG, evals) with space/defence best practices.
- **Learning:** Gain hands-on experience with agent orchestration (LangGraph), MCP, RAG, policy (OPA), GitOps, and observability (OTel, Jaeger, Prometheus/Grafana).
- **Outcome:** A working pipeline from simulated telemetry/events/logs → triage → investigate → decide → act (ticketing, config PRs) → operational report, with no shell access for the agent and clear safe vs restricted actions.

---

## 2. Assumptions

### Domain & data
- Data is **simulated** (NDJSON/Parquet fixtures); no connection to real spacecraft or ground systems during development.
- Architecture must be **production-ready** (see §4.5 for concrete criteria): same patterns and components as for real telemetry, events, and logs; swapping data sources later is mainly ingest and secrets.
- Subsystems in scope: **ADCS, Power, Thermal, Comms, Payload, Ground** (classifiable by the agent).
- Ground segment is represented by log/event streams (e.g. `ground_logs.ndjson`); no live integration required for MVP.

### Technology & stack
- **Python 3.12** for agent, RAG, evals, and pipeline; optional **TypeScript/Node 20+** for UI and MCP servers if preferred.
- **LangGraph** for agent orchestration (state graph, retry, optional human-in-the-loop); OpenAI Agents SDK is an alternative for a lighter prototype only.
- **MCP** as the only tool boundary: no shell/exec; all actions via dedicated MCP servers (Telemetry, KB, Ticketing, GitOps).
- **Postgres + pgvector** for RAG; optional BM25/hybrid and reranker for quality.
- **DuckDB** acceptable for local analytics and fixture querying; optional Kafka/Redpanda for event stream later.
- **FastAPI** for webhook and run/approval API; optional **Next.js** for Mission Control UI.
- **Secrets:** MVP uses `.env` and rotation; Vault when moving to multiple environments or stricter compliance.

### Process & quality
- **OPA** defines what the agent is allowed to do (allowlist, argument validation); policy lives in OPA, not ad-hoc in application code. In MVP, **fail-closed in code** is the last line of defense: if OPA is down, times out, or errors → treat as deny and escalate (see NF8).
- **GitOps** for configuration changes: PRs to an `ops-config` repo (or subtree); branch protection and signed commits support a two-person rule.
- **Evals** run in CI; prompt-injection suite in KB to test that the agent rejects malicious or manipulative content.
- **Observability** from the start: OTel (traces/logs/metrics), Jaeger, Prometheus/Grafana via Docker Compose.

### Scope & constraints
- MVP starts with **1–2 MCP servers** (e.g. Telemetry + KB); Ticketing and GitOps added in later phases.
- No direct human-in-the-loop in the graph required for MVP; approval is via API/UI for restricted actions after the run.
- Single-tenant, single-environment focus for MVP; multi-region or multi-mission is out of scope initially.

---

## 3. Plans (high-level)

### Phase 0 — Foundation (weeks 1–2)
Set up repo structure, Docker (Postgres + pgvector, optional OTel/Jaeger), FastAPI ingest webhook, NDJSON fixtures, and CI (lint, tests).

### Phase 1 — Agent + 2 MCP (weeks 3–4)
LangGraph graph (Triage → Investigate → Decide, no Act). MCP Telemetry and MCP KB (RAG on runbooks/postmortems). First evals (5–10 cases) in CI.

### Phase 2 — Decide + Act (safe) (week 5)
Decide outputs safe vs restricted steps. MCP Ticketing (mock) and MCP GitOps (real PR to ops-config). Agent executes safe actions only; restricted → approval payload. FastAPI approval endpoints.

### Phase 3 — Restricted + OPA + Report (weeks 6–7)
OPA rules (allowlist, argument validation). Restricted actions require OPA allow and UI/API approval. Agent produces operational report (summary, evidence, actions, rollback, trace link). Optional Next.js UI for incidents and approvals.

### Phase 4 — Observability + hardening (week 8)
OTel in agent and API, Prometheus metrics, Grafana dashboard. Prompt-injection suite and evals. Architecture docs and runbooks (e.g. adding MCP, adding eval cases).

### Phase 5 — Post-incident (ongoing)
Postmortem template and KB re-index pipeline. Rule: closed incident → new eval case and CI run.

---

## 4. Requirements

### 4.1 Functional

| ID | Requirement | Priority |
|----|-------------|----------|
| F1 | Ingest: accept telemetry, events, ground logs via webhook or CLI (NDJSON); validate and persist to `data/` or DuckDB. | Must |
| F2 | Triage: classify incident by subsystem (ADCS/Power/Thermal/Comms/Payload/Ground) and risk (impact, likelihood, time-criticality); store incident record. | Must |
| F3 | Investigate: agent can query telemetry (time range, channels), events, runbooks (RAG), postmortems (RAG); output hypotheses and citations. | Must |
| F4 | Decide: produce a plan with safe and restricted actions; safe = ticket, report, extra queries; restricted = config change, component restart, threshold change. | Must |
| F5 | Act (safe): create ticket (mock or real), create PR to ops-config when plan says so; no execution of restricted without approval. | Must |
| F6 | Act (restricted): after OPA allow, create approval request; execution only after approve via API/UI. | Must |
| F7 | Report: generate operational brief (executive summary, evidence, proposed actions, rollback, link to trace). | Must |
| F8 | Approval API: `GET /approvals`, `POST /approvals/:id/approve`, `POST /approvals/:id/reject` (idempotent approve/reject; audit who approved and when). | Must |
| F9 | Post-incident: add postmortem to KB; re-index; add eval case and run evals in CI. | Should |
| F10 | **Escalate-to-human:** when confidence &lt; threshold, missing evidence, conflicting signals, policy deny, or timeout, agent produces an **escalation packet** (what we know, what we don’t, what to check). No “agent was wrong, too bad”; clear handoff path. | Must |

### 4.2 Non-functional

| ID | Requirement | Priority |
|----|-------------|----------|
| NF1 | Agent has **no shell or exec** access; only MCP tools. | Must |
| NF2 | All agent actions appear in **traces** (e.g. Jaeger) and **audit log** (append-only). | Must |
| NF3 | **OPA** enforces tool allowlist and argument validation (e.g. no "restart all", no overly broad time range without approval). | Must |
| NF4 | **Evals** run in CI (e.g. GitHub Actions); at least triage correctness and citation presence; injection suite must not trigger unsafe actions. | Must |
| NF5 | RAG uses **reranker** (local or API) to improve citation quality. | Should |
| NF5a | **Citation grounding check:** every plan step must reference at least one `doc_id` or telemetry/snippet ID. System enforces evidence even when retrieval is simple (no reranker in MVP). | Must |
| NF6 | **Token/rate limits and timeouts** to control cost and latency; fallback to escalate-to-human when limits hit or timeout. Prevents runaway loops and “frozen ops” in critical systems. | Must |
| NF7 | **Documentation:** architecture overview, how to add a new MCP, how to add an eval case. Part of the system; required for system-thinking and onboarding. | Must |
| NF8 | **Fail-closed default:** if OPA is unavailable, times out, or errors → action is **denied**, incident goes to escalation (escalation packet). No “best effort” execution when policy cannot be evaluated. | Must |
| NF9 | **AuthN/AuthZ for approvals:** approval endpoints require authentication (e.g. API key / token in MVP); audit who approved/rejected and when. | Must |

### 4.3 Policy (“production vibe”)

| # | Policy | Implementation |
|---|--------|----------------|
| P1 | No shell access | Only MCP invocations; no shell/exec tool. |
| P2 | Tool allowlist | OPA or config: only listed tool names allowed; others rejected. |
| P3 | Argument validation | OPA: e.g. forbid "restart all", restrict wide time ranges. |
| P4 | Restricted = approval | All restricted actions go to `approval_requests`; execution only after explicit approve (API/UI). |
| P5 | Trace + audit | Every agent action: span in Jaeger; append-only audit log (see §4.6). |
| P6 | Fail-closed on OPA | OPA down/timeout/error → deny + escalation; no execution without policy result. |

### 4.4 Measures of Effectiveness / Measures of Performance

Without these, the system is “it works” rather than “it works better”; MBSE requires measurable criteria.

| ID | Measure | Description | Target (MVP) |
|----|---------|-------------|--------------|
| MoE1 | **Triage accuracy** | Subsystem correct @ top-1 and top-2 | Track in evals; threshold in scoring |
| MoE2 | **Citation precision** | Citations actually support the decision (manual or heuristic check in evals) | Plan steps reference doc_id/snippet; evals flag unsupported steps |
| MoE3 | **Unsafe-action rate** | Any unsafe or off-policy action in evals | **0** (evals must fail if &gt; 0) |
| MoE4 | **Escalation correctness** | Escalation packet produced when required (low confidence, deny, timeout) | Eval cases for “must escalate” scenarios |
| MoP1 | **Mean latency per incident** | End-to-end time from ingest to report | Logged; dashboard (Grafana) |
| MoP2 | **Tool-call count per run** | Number of MCP calls per incident | Logged; upper limit / alert to detect loops |

### 4.5 Production-ready criteria (concrete)

“Architecture must be production-ready” means the repo satisfies:

- **Single-command local run:** e.g. `make run` or `docker-compose up` brings up everything needed to run the pipeline.
- **Reproducible fixtures:** committed NDJSON/Parquet under `data/`; same fixtures produce same ingest outcome.
- **Deterministic evals:** evals are reproducible (pinned model or seed where applicable); CI runs same cases every time.
- **Pinned deps + lockfile:** `requirements.txt` with versions and/or `poetry.lock` / `pipenv.lock`; no floating deps in CI.
- **Structured logging:** JSON or key-value logs (e.g. OTel); no free-form-only logs for agent and API.

### 4.6 Audit log (append-only): schema and storage

- **Purpose:** Credible, immutable record of who did what and what was decided.
- **Event schema (per entry):** `timestamp`, `trace_id`, `incident_id`, `actor` (agent | human), `tool`, `args_hash`, `decision` (e.g. allow/deny/escalate), `policy_result` (OPA allow/deny/error), `outcome` (success/failure/skipped).
- **Storage:** MVP may use a single NDJSON file (append-only) or a DB table with no update/delete. Process must only append; no in-place edits. Enables integrity and later compliance review.

### 4.7 Out of scope (MVP)

- Real spacecraft or ground segment connectivity.
- Vault (use `.env` and rotation for MVP).
- Kafka/Redpanda (webhook + files + DuckDB sufficient for MVP).
- Full 24/7 SOC workflow, notifications, SLA tracking.
- Multi-tenant or multi-mission support.

---

*Document maintained with project_doc.md and roadmap. Update when assumptions or requirements change.*

