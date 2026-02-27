# SpaceOps Mission Agent Lab — Post-MVP Roadmap (Productionization & Scale-Up)

**Purpose:** turn SpaceOps from a working MVP into a **production-grade reference implementation** (incident → decision → evidence), and only then add “showcase” layers (UI, streaming, space realism, GPU, K8s/GitOps, cloud).

> This roadmap is intended to start **after** the current sprint roadmap is completed (or to absorb it if you decide to re-baseline).

---

## Guiding Principles (to avoid burning time and money)
- **Value first:** ship an end-to-end operational slice before adding new tech.
- **Single LLM abstraction:** all model access goes through an **LLM Gateway** (swappable backends).
- **Fail-closed by default:** missing evidence / tool failure / policy deny ⇒ **escalate**, do not act.
- **Evidence over vibes:** every conclusion must point to sources (KB/tool outputs) or escalate.
- **Cost guardrails:** GPU and cloud are optional accelerators; default OFF; TTL + scale-to-zero.
- **UI is operational tooling:** shorten time-to-decision and surface evidence; avoid “frontend projects”.
- **Reproducibility:** every run has `run_id`, captured inputs/outputs, and replay capability.

---

## Scope
### In-scope (reference-grade)
- Incident ingestion, storage, agent runs, evidence-grounded reporting, escalation packets
- Observability (OTel), audit trail, replayability, eval gates in CI
- Safety controls (policy + approvals) for any write actions

### Out-of-scope (for this repo)
- Real commanding of spacecraft/critical infrastructure
- Handling classified/sensitive data
- Heavy compliance frameworks (can be documented as “how you would do it”)

---

## Phase 0 — Core Operational MVP (Local, Reproducible, Evidence-First)
**Outcome:** `docker compose up` → ingest → agent run → report + evidence + traces + replay.

### Entry criteria
- Current sprint roadmap core is complete enough to run end-to-end locally.

### Deliverables
- [ ] **Data Contracts v1** (Pydantic + exported JSON Schemas) with versioning rules:
  - [ ] `TelemetryEvent.v1`
  - [ ] `Incident.v1`
  - [ ] `AgentReport.v1`
  - [ ] `EscalationPacket.v1`
- [ ] Ingest API (NDJSON/events) with schema validation + dedupe (`event_id` unique)
- [ ] Postgres stores (with migrations, e.g. Alembic) so schema evolution is auditable:
  - [ ] `telemetry_events` (append-only)
  - [ ] `incidents`
  - [ ] `runs` (run metadata)
  - [ ] `audit_log` (append-only, per step/tool call)
- [ ] Agent pipeline: **Triage → Investigate → Decide → Report**
- [ ] **Escalation Packet** (mandatory triggers):
  - [ ] missing evidence
  - [ ] conflicting signals
  - [ ] low confidence
  - [ ] tool timeout/failure
- [ ] **LLM Gateway (minimum)**:
  - [ ] `generate()` + tool-calling interface
  - [ ] backend: `openai` (default)
  - [ ] logs: model/version/latency (+ optional cost estimate)
  - [ ] **Implementation note:** prefer reusing a battle-tested gateway such as **LiteLLM**
        (as a sidecar/container) instead of building a custom proxy from scratch; LiteLLM
        provides unified OpenAI-compatible APIs, fallbacks, retries, and spend tracking.
- [ ] **Guardrails (minimum)**:
  - [ ] mandatory escalation when evidence missing
  - [ ] output schema enforcement (report + escalation)
  - [ ] tool allowlist + per-tool timeouts/limits
- [ ] **Observability baseline**:
  - [ ] OTel traces end-to-end
  - [ ] log correlation by `run_id`
  - [ ] Jaeger trace deep links in reports/escalations
- [ ] **Replay tooling (minimum)**:
  - [ ] capture run inputs (event IDs + payload hash) and key outputs
  - [ ] re-run on identical inputs (deterministic seed/metadata)
- [ ] CI gates:
  - [ ] unit tests
  - [ ] at least 1 e2e eval `must_escalate`
- [ ] Demo fixtures: 2 scenarios
  - [ ] Scenario A: clear anomaly → report + evidence + trace link
  - [ ] Scenario B: conflicting/insufficient evidence → escalation + trace link

### Exit criteria (acceptance checks)
- [ ] One-command local run produces both scenarios reliably
- [ ] Every run has evidence or escalates (no “confident hallucinations”)
- [ ] Replay reproduces the same classification + same escalation decision

---

## Phase 1 — Operational UI (Thin Layer)
**Goal:** move from “backend demo” to “ops product”.

### Deliverables
- [ ] UI MVP (Streamlit or minimal web) with:
  - [ ] Incident List (filters: time, sat_id, subsystem, risk, status, confidence)
  - [ ] Incident Detail:
    - [ ] agent summary/report
    - [ ] evidence panel (citations/snippets/doc_id/tool outputs)
    - [ ] event timeline
    - [ ] escalation packet view (known/unknown/next checks)
    - [ ] **run timeline** (triage/investigate/decide/report; durations/status)
    - [ ] Jaeger trace deep link
  - [ ] Replay:
    - [ ] re-run on same input (deterministic)
    - [ ] upload fixture + simulate
- [ ] Non-goals explicitly enforced:
  - [ ] no commanding UI
  - [ ] no “pretty dashboards” without operational value

### Exit criteria
- [ ] A reviewer can diagnose Scenario A/B only from UI + evidence + trace link

---

## Phase 2 — Streaming / Queue (Ground IT Realism)
**Reason:** bursts, backpressure, retry, replay; decouple ingest from workers.

### Option A (Minimal — no Kafka yet)
- [ ] `telemetry_events` remains append-only
- [ ] Worker reads by offset + idempotency keys
- [ ] Transactional processing: fetch → process → persist → advance offset
- [ ] Retry + DLQ-like tables:
  - [ ] `consumer_offsets(consumer_group, partition_key, last_offset, updated_at)`
  - [ ] `dlq_events(event_id, reason, retry_count, next_retry_at, last_error_hash)`

### Option B (Recommended)
- [ ] NATS JetStream **(preferred for SpaceOps/edge realism)** or Redpanda/Kafka
- [ ] Partitioning by `sat_id` and/or subsystem
- [ ] Consumers: triage / enrich / report
- [ ] DLQ + replay tooling

### Space-like simulation (without full CCSDS)
- [ ] contact windows (downlink on/off)
- [ ] drop/dup/out-of-order
- [ ] sequence counters + validity flags (CRC-like)
- [ ] replay buffered telemetry

### Exit criteria
- [ ] Backpressure does not crash ingest
- [ ] Replay works across queued events
- [ ] DLQ captures and explains failures

---

## Phase 3 — Space Protocol Realism Adapter (Optional)
**Goal:** demonstrate space-link vs ground IT difference without changing the core.

### Deliverables
- [ ] Adapter: “CCSDS-like” frames/packets → **internal `TelemetryEvent.v1`**
- [ ] Core remains unchanged (stable ingest contract)

### Exit criteria
- [ ] Same demo scenarios run with both: plain NDJSON input and CCSDS-like adapter input

---

## Phase 4 — Safety Controls + Quality Gates (Serious Mode)
**Outcome:** controlled risk + measurable behavior in CI.

### Guardrails (expanded)
- [ ] Evidence policy: grounding required; no invented citations
- [ ] Mandatory escalation when:
  - [ ] evidence missing
  - [ ] tool failed/timeout
  - [ ] contradictions detected
- [ ] Strict output schemas everywhere (report, escalation, tool results envelope)
- [ ] Prompt injection hardening:
  - [ ] tool input sanitization
  - [ ] allowlists for tool parameters
  - [ ] safe rendering (no tool instructions from user content)
  - [ ] evaluate adopting a dedicated guardrails engine (e.g. Nvidia NeMo Guardrails or
        an LLM firewall such as Lakera Guard) instead of only bespoke regex/prompt rules.

### Quality gates (expanded)
- [ ] Evals in CI that block regressions:
  - [ ] citations required when `require_citations=true`
  - [ ] subsystem classification top-k expectations
  - [ ] must_escalate cases
  - [ ] tool failure must set correct audit outcome (failure vs empty)
  - [ ] where needed, use **LLM-as-a-judge** / semantic metrics (e.g. LangSmith/RAGAS-style)
        instead of strict string equality, to allow multiple correct answers while still
        catching regressions.
- [ ] Golden runs suite (replay + snapshots)
- [ ] Basic “behavior metrics” emitted:
  - [ ] escalation rate
  - [ ] evidence coverage rate
  - [ ] p95 latency per stage

### Exit criteria
- [ ] CI reliably fails when evidence/citations regress
- [ ] Tool failures are visible and distinguishable in audit + metrics

---

## Phase 5 — LLM Backends (Vendor-Agnostic) + Optional GPU (OFF by Default)
**Goal:** GPU is an optional accelerator, not permanent infra.

### LLM Gateway (complete)
- [ ] Backends: `openai` (default) + `gpu` (optional)
- [ ] Feature flag: `LLM_BACKEND=openai|gpu`
- [ ] Healthcheck + fallback to OpenAI when GPU unavailable
- [ ] Circuit breaker for GPU backend
- [ ] Logged metadata: model/version, latency, token usage/cost estimates

### GPU inference service (separate)
- [ ] NVIDIA NIM (fast path) **or** TensorRT-LLM/Triton (perf path)
- [ ] Endpoint + `/health`
- [ ] Compose profile: `--profile gpu` + `make gpu-up/gpu-down`

### Cost guardrails
- [ ] stop-by-default + scale-to-zero
- [ ] TTL auto-shutdown after inactivity (30–60 min)
- [ ] budget cap + alerting (even simple thresholds)

### Exit criteria
- [ ] System works identically with `openai` and `gpu` backends (within defined tolerances)

---

## Phase 6 — Kubernetes + GitOps (After MVP is Stable)
**Goal:** demonstrate operational maturity: rollout, policies, scaling, secrets.

### K8s Local Proof
- [ ] kind/k3d cluster
- [ ] Helm/kustomize: API, workers, Postgres, OTel collector, Jaeger
- [ ] One-command up: `make k8s-up`

### “Real ops” controls
- [ ] HPA for workers
- [ ] NetworkPolicy
- [ ] Policies (OPA Gatekeeper or Kyverno) for guardrails
- [ ] Secrets (SOPS or External Secrets)
  - [ ] for enterprise deployments, consider **External Secrets Operator (ESO)** integrated
        with a managed secrets backend (e.g. Google Secret Manager, HashiCorp Vault) so that
        rotation of tokens (Jira/GitHub/etc.) is automated.

### Optional GitOps
- [ ] Argo CD or Flux with repo-driven deploy

### Exit criteria
- [ ] Safe rollout + rollback documented and demonstrated locally

---

## Phase 7 — Cloud Deployment (GCP-First, Sensible Costs)
**Goal:** cloud “showcase” without burning money.

### CPU stack on GCP (cheap/free-ish)
- [ ] Cloud Run for API + UI
- [ ] Artifact Registry
- [ ] Terraform minimal (project, SA, deploy)
- [ ] End-to-end observability preserved (OTel)

### GPU on-demand
- [ ] Option A: Cloud Run GPU (scale-to-zero) if available
- [ ] Option B: external GPU provider for inference only
- [ ] Gateway routes by feature flag

### Billing hygiene
- [ ] budgets + alerts
- [ ] hard monthly cap where possible
- [ ] auto shutdown routines

### Exit criteria
- [ ] Demo scenarios run in cloud with traces + evidence + replay

---

## Cross-Cutting Engineering Artifacts (Portfolio-Grade)
- [ ] **README (1 page)**: architecture + run locally + 2 demo scenarios + screenshots
- [ ] **Runbook**: how to debug a run (logs/traces/audit), how to add a tool, how to add a scenario
- [ ] **ADR log** (3–6 decisions): gateway, queue choice, policy model, replay strategy
- [ ] **Threat model** (1 page): prompt injection, tool abuse, data poisoning, secrets leakage
- [ ] Basic dependency hygiene:
  - [ ] pinned dependencies
  - [ ] SBOM or dependency scanning (minimal)

---

## Technical Debt Management

Some roadmap items are really about **managing long-term technical debt**, especially in an
LLM-heavy, safety-critical system like SpaceOps. Treat these as ongoing themes rather than
one-off tasks:

- **Model & prompt lifecycle:** plan for model deprecation/migration, shadow testing of new models,
  and a versioned prompt registry instead of inline prompts only in code.
- **Reliability patterns:** central retries/backoff and circuit-breakers for MCP and external HTTP
  calls; chaos/degradation testing (e.g. Toxiproxy) to validate escalation behaviour under failure.
- **Infra/Sec hygiene:** keep dependency hygiene and secret management (e.g. future Vault/Secrets
  manager work) under a recurring “tech debt” stream, not only as optional backlog.
- **Tech-debt budget:** after S2, reserve a fixed percentage of sprint capacity for refactors,
  dead-code removal, and maintainability improvements, and use evals to guard against regressions.

---

## Ideas (backlog / future)
- **GitOps deployment on K8s (Argo CD / Flux):** repo-driven deploy, sync from `ops-config` (or app manifests); CD for agent, MCPs, and ops-config changes.
- **Model monitoring (Langfuse):** LLM observability (latency, token usage, cost), trace per run, prompt/response logging and evaluation hooks.
- **Service mesh for K8s (Istio / Linkerd):** mTLS between services, traffic shaping for agent/MCP calls, retries/timeouts at mesh layer, and richer telemetry for policy/debugging.
- **Fine-tuning / reinforcement fine-tuning:** task-specific adapters or fine-tuned models for anomaly triage/reporting, with RLHF/RLAIF-style feedback loops driven by evals and human-in-the-loop labels (on top of the LLM Gateway, not baked into core logic).

---

## Definition of Done (Portfolio-Grade)
- [ ] `docker compose up` → both demo scenarios succeed end-to-end
- [ ] Evidence-grounded reports (citations), otherwise mandatory escalation
- [ ] Escalation packet exists and is covered by an automated test/eval
- [ ] Traceable runs (Jaeger link) + `run_id` correlation everywhere
- [ ] Replay tooling + golden runs
- [ ] UI MVP shows incidents + evidence + trace link + run timeline
- [ ] CI blocks regressions (unit + e2e eval gates)