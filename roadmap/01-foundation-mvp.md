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
| **S1.1** | Create directory structure: `apps/api`, `apps/agent`, `apps/mcp/telemetry_server`, `apps/mcp/kb_server`, `data/`, `kb/runbooks`, `kb/postmortems`, `evals`, `infra`, `docs`. | [ ] |
| **S1.2** | Add `infra/docker-compose.yml`: Postgres 15+ pgvector, OTel Collector, Jaeger. Single command to start all. | [ ] |
| **S1.3** | Pinned deps + lockfile (e.g. requirements.txt with versions or poetry.lock). | [ ] |
| **S1.4** | FastAPI: `GET /health`, `POST /ingest` (NDJSON validate + persist); trigger run (e.g. POST with incident payload). | [ ] |
| **S1.5** | Reproducible NDJSON fixtures in `data/telemetry`, `data/events`, `data/ground_logs` (2–3 records each). | [ ] |
| **S1.6** | MCP Telemetry: `query_telemetry(time_range, channels)`; MCP KB: `search_runbooks`, `search_postmortems` (RAG pgvector); index 2–3 runbooks, 1 postmortem. | [ ] |
| **S1.7** | LangGraph: Triage (subsystem + risk) → Investigate (Telemetry + KB, citations) → Decide (plan; each step must reference doc_id or snippet — NF5a) → Report (summary, evidence, actions, rollback, trace URL). | [ ] |
| **S1.8** | Escalation path (F10): low confidence / no evidence / conflict / timeout → generate escalation packet; no silent failure. | [ ] |
| **S1.9** | Audit log: append-only NDJSON or table; schema: timestamp, trace_id, incident_id, actor, tool, args_hash, decision, policy_result, outcome. | [ ] |
| **S1.10** | OTel in agent + API; traces to Jaeger. Structured logging (JSON/key-value). | [ ] |
| **S1.11** | Evals: 5–10 cases (triage top-1/top-2, citation present, one “must escalate”); `evals/scoring.py`; CI job; deterministic. | [ ] |
| **S1.12** | Token/rate limits and timeouts (NF6); fallback to escalate when hit. | [ ] |
| **S1.13** | pre-commit (ruff, mypy); GitHub Actions: lint, pytest, evals. README: how to run, how to call ingest, how to run tests. | [ ] |

### Definition of done (Sprint 1)
- [ ] Single command brings up stack; ingest → triage → investigate → decide → report runs; report includes trace link.
- [ ] Escalation packet produced when conditions (low confidence, timeout, etc.) are met.
- [ ] Audit log has correct schema; append-only.
- [ ] Evals run in CI; triage and citation (and escalation) covered.
- [ ] Traces visible in Jaeger.

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
| **S2.1** | Create or clone `ops-config` repo (or subtree): sample config (e.g. alert thresholds YAML). | [ ] |
| **S2.2** | MCP Ticketing: `create_ticket(title, body)` (mock); MCP GitOps: `create_pr(repo_path, branch, files)` (real PR). | [ ] |
| **S2.3** | Extend Decide: steps safe vs restricted; Act: execute safe (ticket, PR); for restricted → call OPA. | [ ] |
| **S2.4** | OPA: allowlist + argument validation (e.g. no "restart all"); endpoint `POST /v1/data/agent/allow`. **Fail-closed:** on OPA error/timeout/unavailable → deny + escalation packet (NF8). | [ ] |
| **S2.5** | If OPA allow: create approval request in DB. Approval API: `GET /approvals`, `POST /approvals/:id/approve`, `POST /approvals/:id/reject` — **idempotent** (repeated approve same id = same result); require **auth** (API key/token); record **who** approved/rejected and **when** in audit. | [ ] |
| **S2.6** | On approve: execute restricted action (e.g. GitOps MCP); write result to audit log. | [ ] |
| **S2.7** | Audit log: approval events with actor=human, tool, decision, outcome. | [ ] |
| **S2.8** | Injection suite: `evals/injection_suite/` — 5–10 docs (fake runbooks) that try to trigger unsafe/off-policy actions; evals must fail if unsafe-action rate &gt; 0. | [ ] |
| **S2.9** | Prometheus metrics: `agent_runs_total`, `agent_run_duration_seconds`, `agent_errors_total`, tool-call count per run; Grafana dashboard. | [ ] |
| **S2.10** | Unit tests for OPA policies (allowlist, forbidden args, fail-closed behavior). | [ ] |

### Definition of done (Sprint 2)
- [ ] Safe actions create ticket and PR; restricted go through OPA → allow → approval → execution; OPA failure → deny + escalation.
- [ ] Approval endpoints are idempotent and require auth; audit records who/when.
- [ ] Injection suite in CI; unsafe-action rate = 0 required.
- [ ] Metrics and dashboard show run count, latency, tool-call count.

---

## Phase 4 — Hardening (after Sprint 2)

**Goal:** Documentation (architecture + runbooks), expanded evals, optional UI; production-ready criteria fully met.

### Tasks (backlog)
- [ ] `docs/architecture.md`: component diagram, data flow, tech choices.
- [ ] Runbook: “How to add a new MCP” (template, registration, agent wiring).
- [ ] Runbook: “How to add an eval case” (cases.yaml, scoring.py, CI).
- [ ] Reranker for RAG (NF5) if not in S1/S2.
- [ ] Optional Next.js: incident list, approval list, Approve/Reject with auth.
- [ ] Expand eval suite (e.g. 20–30 cases); citation precision / MoE in scoring.
- [ ] Post-incident loop: postmortem template, KB re-index, new eval case per incident.

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
