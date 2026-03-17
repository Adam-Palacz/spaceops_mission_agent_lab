# SpaceOps Mission Agent Lab — Roadmap: Sprints, Goals & Tasks

Sprints are **2 weeks** each. **Core delivery in 2 sprints** (S1 + S2); Phase 4 hardening follows. Each sprint has a **Goal**, **Outcomes**, and **Tasks** with clear acceptance.

---

## Epic overview

| Epic | Sprints | Goal |
|------|---------|------|
| **E0** Core pipeline | S1 | Ingest → Triage → Investigate → Decide → Report + basic evals + OTel traces |
| **E1** Act + policy + safety | S2 | Act (safe) + GitOps PR + approvals + OPA (fail-closed) + injection suite + dashboards |
| **E2** Hardening | Phase 4 | Docs, runbooks, expanded evals, optional UI |

---

## Sprint 1 — Full pipeline to Report (Weeks 1–2)

**Sprint goal:** One command runs the stack; ingest → triage → investigate → decide → report works end-to-end with basic evals and OTel traces. No act yet; evidence and escalation path in place.

### Outcomes
- Single-command local run (e.g. `make run` or `docker-compose up`); pinned deps + lockfile; reproducible fixtures.
- Repo structure (apps/, data/, kb/, evals/, infra/, docs/); Postgres + pgvector; OTel Collector + Jaeger.
- FastAPI: health, ingest webhook; agent trigger (e.g. POST or CLI with `incident_<id>.json`).
- LangGraph: Triage → Investigate (Telemetry MCP + KB MCP) → Decide (plan with citation grounding) → **Report** (summary, evidence, actions, rollback, trace link).
- **Escalation:** when confidence &lt; threshold, missing evidence, conflict, or timeout → escalation packet (what we know, what we don’t, what to check).
- Audit log: append-only; schema with timestamp, trace_id, incident_id, actor, tool, args_hash, decision, policy_result, outcome.
- Basic evals (triage + citation presence + “must escalate” cases); evals run in CI; deterministic.
- Structured logging (OTel); traces visible in Jaeger for a full run.

### Tasks

| Task | Description | Done |
|------|-------------|------|
| **S1.1** | Create directory structure: `apps/api`, `apps/agent`, `apps/mcp/telemetry_server`, `apps/mcp/kb_server`, `data/`, `kb/runbooks`, `kb/postmortems`, `evals`, `infra`, `docs`. | [x] |
| **S1.2** | Add `infra/docker-compose.yml`: Postgres 15+ pgvector, OTel Collector, Jaeger. Single command to start all. | [x] |
| **S1.3** | Pinned deps + lockfile (e.g. requirements.txt with versions or poetry.lock). | [x] |
| **S1.4** | FastAPI: `GET /health`, `POST /ingest` (NDJSON validate + persist); trigger run (e.g. POST with incident payload). | [x] |
| **S1.5** | Reproducible NDJSON fixtures in `data/telemetry`, `data/events`, `data/ground_logs` (2–3 records each). | [x] |
| **S1.6** | MCP Telemetry: `query_telemetry(time_range, channels)`; MCP KB: `search_runbooks`, `search_postmortems` (RAG pgvector); index 2–3 runbooks, 1 postmortem. | [x] |
| **S1.7** | LangGraph: Triage (subsystem + risk) → Investigate (Telemetry + KB, citations) → Decide (plan; each step must reference doc_id or snippet — NF5a) → Report (summary, evidence, actions, rollback, trace URL). | [x] |
| **S1.8** | Escalation path (F10): low confidence / no evidence / conflict / timeout → generate escalation packet; no silent failure. | [x] |
| **S1.9** | Audit log: append-only NDJSON or table; schema: timestamp, trace_id, incident_id, actor, tool, args_hash, decision, policy_result, outcome. | [x] |
| **S1.10** | OTel in agent + API; traces to Jaeger. Structured logging (JSON/key-value). | [x] |
| **S1.11** | Evals: 5–10 cases (triage top-1/top-2, citation present, one “must escalate”); `evals/scoring.py`; CI job; deterministic. | [x] |
| **S1.12** | Token/rate limits and timeouts (NF6); fallback to escalate when hit. | [x] |
| **S1.13** | pre-commit (ruff, mypy); GitHub Actions: lint, pytest, evals. README: how to run, how to call ingest, how to run tests. | [x] |

### Definition of done (Sprint 1)
- [x] Single command brings up stack; ingest → triage → investigate → decide → report runs; report includes trace link.
- [x] Escalation packet produced when conditions (low confidence, timeout, etc.) are met.
- [x] Audit log has correct schema; append-only.
- [x] Evals run in CI; triage and citation (and escalation) covered.
- [x] Traces visible in Jaeger.

---

## Sprint 2 — Act, approvals, OPA, injection suite, dashboards (Weeks 3–4)

**Sprint goal:** Safe actions execute (ticket + GitOps PR); restricted require OPA allow + approval; approval API is idempotent and authenticated; fail-closed on OPA failure; injection suite + dashboards prove safety and observability.

### Outcomes
- MCP Ticketing (mock) and MCP GitOps (real PR to ops-config).
- Decide output: steps tagged safe vs restricted; Act executes safe only; restricted → OPA check → if allow, approval request; if OPA down/timeout/error → deny + escalation (NF8).
- Approval API: idempotent approve/reject; AuthN (e.g. API key/token); audit who approved and when (NF9).
- Audit log includes approval events (actor=human, decision, outcome).
- Report already in S1; ensure it’s still produced and linked to trace.
- Injection suite: 5–10 KB docs that try to force bad actions; evals require unsafe-action rate = 0.
- Prometheus metrics (run count, latency, tool-call count); Grafana dashboard.

### Tasks

| Task | Description | Done |
|------|-------------|------|
| **S2.1** | Create or clone `ops-config` repo (or subtree): sample config (e.g. alert thresholds YAML). | [x] |
| **S2.2** | MCP Ticketing: `create_ticket(title, body)` (mock); MCP GitOps: `create_pr(repo_path, branch, files)` (real PR). | [x] |
| **S2.3** | Extend Decide: steps safe vs restricted; Act: execute safe (ticket, PR); for restricted → call OPA. | [x] |
| **S2.4** | OPA: allowlist + argument validation (e.g. no "restart all"); endpoint `POST /v1/data/agent/allow`. **Fail-closed:** on OPA error/timeout/unavailable → deny + escalation packet (NF8). | [x] |
| **S2.5** | If OPA allow: create approval request in DB. Approval API: `GET /approvals`, `POST /approvals/:id/approve`, `POST /approvals/:id/reject` — **idempotent** (repeated approve same id = same result); require **auth** (API key/token); record **who** approved/rejected and **when** in audit. | [x] |
| **S2.6** | On approve: execute restricted action (e.g. GitOps MCP); write result to audit log. | [x] |
| **S2.7** | Audit log: approval events with actor=human, tool, decision, outcome. | [x] |
| **S2.8** | Injection suite: `evals/injection_suite/` — 5–10 docs (fake runbooks) that try to trigger unsafe/off-policy actions; evals must fail if unsafe-action rate &gt; 0. | [x] |
| **S2.9** | Prometheus metrics: `agent_runs_total`, `agent_run_duration_seconds`, `agent_errors_total`, tool-call count per run; Grafana dashboard. | [x] |
| **S2.10** | Unit tests for OPA policies (allowlist, forbidden args, fail-closed behavior). | [x] |

### Definition of done (Sprint 2)
- [x] Safe actions create ticket and PR; restricted go through OPA → allow → approval → execution; OPA failure → deny + escalation.
- [x] Approval endpoints are idempotent and require auth; audit records who/when.
- [x] Injection suite in CI; unsafe-action rate = 0 required.
- [x] Metrics and dashboard show run count, latency, tool-call count.

---

## Sprint 3 — Observability, resilience, and tech-debt (Weeks 5–6)

**Sprint goal:** Add observability and lifecycle “spine” around the agent (LLM observability, prompt registry, model upgrade hooks, context compaction), harden external interactions (retry/circuit breaker, chaos harness), and introduce process guardrails (automated dependency updates, secrets plan, tech-debt budget) without breaking existing eval guarantees.

### Outcomes
- LLM observability spine: internal API (`apps/llm_observability.py`) to log runs and calls (run_id, node, model_id, prompt_id/version, eval IDs) in NDJSON + OTel spans.
- Prompt registry & versioning: prompts moved to `prompts/registry.py` with stable IDs and versions; agent nodes reference them instead of inline strings.
- Model lifecycle hooks: config and script for shadow-testing (`agent_model_id`, `agent_candidate_model_ids`, `python -m evals.shadow_models`) to compare current vs candidate models offline.
- Context-window compaction: `compact_history` trims hypotheses/citations after each node based on config to keep runs within NF6 limits.
- Resilience layer: HTTP/MCP retry with exponential backoff + jitter and a circuit breaker, applied to OPA and MCP clients.
- Chaos/degradation harness: tests that simulate slow/unavailable MCP and OPA outages, asserting escalation/fail-closed behaviour.
- Automated dependency updates: Dependabot for pip + Actions, gated by CI (ruff, mypy, pytest, evals).
- Secrets management stub + plan: `apps/common/secrets.py` and `docs/secrets.md` prepare a path from `.env` to a real secrets backend.
- Tech-debt budget process: `docs/process.md` codifies ~20% sprint capacity for tech-debt items and shows how Sprint 3 tasks (S3.4–S3.8) fit this budget.

### Tasks

| Task | Description | Done |
|------|-------------|------|
| **S3.0** | LLM observability spine (Langfuse-compatible) for runs/calls with prompt/model metadata. | [x] |
| **S3.1** | Model upgrade / shadow-testing pipeline (config + `evals.shadow_models` script; full rollout deferred to Phase 4 P4.8). | [x] |
| **S3.2** | Prompt registry & versioning (central `prompts/registry.py`, prompt IDs/versions, docs). | [x] |
| **S3.3** | Context window & memory compaction (hypotheses/citations caps + integration in LangGraph). | [x] |
| **S3.4** | MCP/HTTP retry & circuit breaker layer (shared helpers; wired to OPA + MCP clients). | [x] |
| **S3.5** | Chaos / degradation test harness (MCP/OPA failure scenarios with assertions on escalation/fail-closed). | [x] |
| **S3.6** | Automated dependency updates (Dependabot configuration, CI gating, review policy). | [x] |
| **S3.7** | Secrets management plan & integration path (secrets abstraction + migration doc). | [x] |
| **S3.8** | Tech-debt budget process & documentation (~20% rule, examples, planning snippet). | [x] |

### Definition of done (Sprint 3)
- [x] LLM observability spine records runs and calls with prompt/model metadata and integrates with OTel spans.
- [x] Prompt registry centralises and versions prompts used by the agent.
- [x] Context compaction is applied after each node and covered by tests.
- [x] HTTP/MCP retry and circuit breaker wrap OPA and MCP calls without breaking fail-closed semantics.
- [x] Chaos/degradation tests demonstrate correct escalation/fail-closed behaviour under MCP/OPA failures.
- [x] Automated dependency updates are configured and gated by lint, tests, and evals.
- [x] Secrets management abstraction and migration plan are documented and wired into config for key secrets.
- [x] Tech-debt budget process is documented and visible in sprint planning artefacts.

---

## Phase 4 — Hardening (after Sprint 2)

**Goal:** Documentation (architecture + runbooks), expanded evals, optional UI; production-ready criteria fully met.

### Tasks (backlog)
- [ ] `docs/architecture.md`: component diagram, data flow, tech choices. (P4.1)
- [ ] Runbook: “How to add a new MCP” (template, registration, agent wiring). (P4.2)
- [ ] Runbook: “How to add an eval case” (cases.yaml, scoring.py, CI). (P4.3)
- [ ] Reranker for RAG (NF5) if not in S1/S2. (P4.4)
- [ ] Optional Next.js: incident list, approval list, Approve/Reject with auth. (P4.5)
- [ ] Expand eval suite (e.g. 20–30 cases); citation precision / MoE in scoring. (P4.6)
- [ ] Post-incident loop: postmortem template, KB re-index, new eval case per incident. (P4.7)
- [ ] Model upgrade / shadow-testing rollout: scheduled shadow runs, reports, and switch criteria. (P4.8)

### Recurring (ongoing)
- Add `postmortem.md` to `kb/postmortems/` per closed incident; re-index KB.
- Add new eval case per significant incident; CI evals include it.

### Optional backlog
- Human-in-the-loop node in LangGraph.
- Kafka/Redpanda ingest.
- Vault for secrets.

---

## Technical Debt Management (LLM, Resiliency, Infra, Process)

Even with Hardening, technical debt will grow unless it is managed explicitly. The following
themes should be treated as **recurring backlog streams** and pulled into sprints after S2:

- **Model & prompt lifecycle (LLMOps tech debt):**
  - Model upgrade/shadow-testing pipeline for safe migration when providers deprecate models.
  - Prompt registry (versioned prompts outside code, e.g. YAML or external service) instead of ad hoc inline prompts.
  - Context-window optimization: summarization/compaction for long runs and growing KB, to avoid hitting NF6 limits by accident.
- **Resiliency & chaos (reliability debt):**
  - Centralised retry patterns (exponential backoff + circuit breaker) for MCP and other external HTTP calls.
  - Chaos/degradation tests (e.g. Toxiproxy) for MCP servers and DB, verifying correct escalation packets and audit outcomes.
- **Infra/Sec debt:**
  - Automated dependency updates (Dependabot/Renovate) gated by unit tests + eval suite.
  - IaC for non-local environments (Terraform/Tofu and/or Helm charts) instead of ad hoc compose-only setups.
  - Secrets management and rotation via a proper secrets backend (Vault / cloud secrets manager), not `.env` in long term.
- **Process debt:**
  - Tech-debt budget: reserve ~20% of capacity in each post-S2 sprint for refactors, dead-code removal, and readability/maintainability work.

---

## Summary: sprint → deliverables

| Sprint | Main deliverable |
|--------|-------------------|
| **S1** | Ingest → Triage → Investigate → Decide → Report + evals + OTel + audit log + escalation packet |
| **S2** | Act (safe + restricted with OPA + approval), idempotent auth’d approvals, injection suite, dashboards |
| **S3** | Technical debt management: LLM/prompt lifecycle, resiliency patterns, infra/sec hygiene, and process guardrails |
| **Phase 4** | Docs, runbooks, expanded evals, optional UI |

---

*Update this roadmap when sprint scope or priorities change. Align with goals.md (requirements, MoE/MoP, audit schema, production-ready criteria).*

**Task-level execution:** See **[roadmap/](roadmap/)** for phased folders (01-core, 02-hardening), sprint folders (sprint-1, sprint-2), per-task markdown files, and BOARD.md per sprint/phase for status tracking.
