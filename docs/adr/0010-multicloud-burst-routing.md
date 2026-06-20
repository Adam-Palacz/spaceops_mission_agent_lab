# ADR 0010 — Multi-cloud burst routing (portable baseline + optional cloud B)

- **Status:** Accepted (simulation + policy; live multi-cloud deferred)
- **Date:** 2026-06-03
- **Related:** PS7.7, BL-004, [ADR 0004](0004-llm-backend-rollout.md), [ADR 0005](0005-environment-strategy-dev-stage-prod.md), [ADR 0009](0009-gcp-baseline-portable-first.md), PS5.4, PS5.6, PS7.6

## Context

SpaceOps runs a **portable-first** Kubernetes baseline on cloud A (GCP stage per ADR 0009). Phase 7
Stage 4 envisions **optional burst inference** on cloud B (GPU or managed API) without coupling
`apps/` to vendor SDKs.

PS5 delivered a stable **LLM gateway** (`apps/llm_gateway.py`) with backend health fallback (GPU →
OpenAI). PS7.1 proved live GKE stage. BL-004 asks for a written strategy before autonomous
multi-cloud scheduling.

**PS7.7 scope:** ADR + **deterministic policy simulation** + audit field `backend_routing_reason`.
No live cross-cloud networking, identity federation, or second cluster in this sprint.

## Decision

### 1. Architecture pattern — K8s-first + optional burst plane

```
┌─────────────────────────────────────────────────────────────┐
│ Cloud A (primary) — GKE / kind — ADR 0009                   │
│  API / agentWorker · Postgres · NATS · OPA · Jaeger         │
│  LLM gateway (apps/llm_gateway.py)                          │
└───────────────────────────┬─────────────────────────────────┘
                            │ policy + health + budget
                            ▼
              ┌─────────────────────────────┐
              │ Burst routing policy (PS7.7)  │
              │ apps/llm_burst_routing.py     │
              └─────────────┬───────────────┘
                            │
         ┌──────────────────┴──────────────────┐
         ▼                                      ▼
  Primary backend                      Burst backend (cloud B)
  (openai / in-cluster NIM)            (external GPU API / NIM endpoint)
```

**Principles**

- Application code calls **`generate()`** only; no cloud-specific imports in agent nodes.
- Burst capacity is a **backend URL + credentials** behind the gateway registry (same as PS5 GPU).
- Routing policy is **rule-based first**; agentic/autonomous scheduling is out of scope.
- **Kill-switch** env `LLM_BURST_KILL_SWITCH=true` forces primary path in policy simulation and audit.

### 2. Decision inputs (rule order — deterministic)

Policy evaluation (`decide_burst_route`) uses fixed precedence:

| Order | Input | Effect |
|-------|--------|--------|
| 1 | `kill_switch` | Route primary; reason `kill_switch_active` |
| 2 | `burst_enabled=false` | Route primary; reason `burst_disabled` |
| 3 | `budget_ok=false` | Route primary; reason `budget_exceeded` (PS7.6 guardrails) |
| 4 | `burst_healthy=false` | Route primary; reason `burst_unavailable` |
| 5 | `burst_within_cost_ceiling=false` | Route primary; reason `burst_cost_ceiling` |
| 6 | `burst_latency_p95_ms > latency_sla_ms` | Route primary; reason `burst_latency_sla` |
| 7 | `primary_healthy=false` and burst healthy | Route burst; reason `primary_unhealthy_burst_takeover` |
| 8 | default (all gates pass) | Route burst; reason `burst_policy_match` |

Same inputs → same decision (simulation tests in `tests/test_multicloud_burst_ps77.py`).

### 3. Safe fallback (no unsafe Act)

When burst is unavailable or policy denies burst:

- **LLM path:** existing PS5.4 behavior — GPU preflight/timeout/error → OpenAI fallback **or** escalation via `LLMBudgetExceededError` / `LLMGatewayProviderError` (no silent cross-cloud hop).
- **Agent Act path:** unchanged — OPA + approval; burst routing never bypasses policy.
- **Ingest / queue:** unchanged — NATS-first (ADR 0002); burst is **inference-only**.

If OpenAI fallback is impossible (no API key), fail closed with `LLMGatewayProviderError`.

### 4. Audit and observability

Each successful `generate()` records:

| Field | Where |
|-------|--------|
| `backend_requested`, `backend_actual`, `fallback_used`, `fallback_reason` | Gateway return, logs (ADR 0004) |
| **`backend_routing_reason`** | Gateway return, logs, `record_gateway_provenance` (PS7.7) |

Reason vocabulary: `kill_switch_active`, `burst_disabled`, `configured:<backend>`, `fallback:<reason>`,
`policy:<simulated_reason>` when burst policy audit is enabled.

**KPIs (future dashboards):**

- `llm_tokens_total`, `llm_estimated_cost_usd_total` by backend (PS5.6)
- `llm_backend_fallback_total` (PS5.4)
- routing reason counts from structured logs / audit aggregation

### 5. Security and networking (live burst — deferred)

Documented constraints for Phase 7 live burst:

- **Identity:** workload identity on cloud A; burst endpoint uses scoped API key / OIDC federation (no long-lived keys in Git).
- **Secrets:** ESO/GSM per ADR 0007; burst credentials in separate secret key `burstLlmApiKey`.
- **Network:** egress allowlist to burst endpoint only; no inbound from cloud B to Postgres.
- **Audit:** `backend_routing_reason` + existing NDJSON audit log; cross-cloud trace via OTel `trace_id`.

### 6. Rollout plan

| Stage | Activity | PS7.7 |
|-------|----------|-------|
| **0 — Policy simulation** | `python scripts/simulate_multicloud_burst_routing.py` | **Done** |
| **1 — Shadow audit** | Log `backend_routing_reason` on every gateway call | **Done** |
| **2 — Controlled burst** | Point `GPU_LLM_BASE_URL` at cloud B endpoint; `LLM_BURST_ENABLED=true` | Phase 7 |
| **3 — Production fraction** | Canary % traffic via gateway flags | Phase 7+ |

### 7. Kill-switch and rollback

| Mechanism | Env / action |
|-----------|----------------|
| **Kill-switch** | `LLM_BURST_KILL_SWITCH=true` → policy + audit reason `kill_switch_active` |
| **Disable burst** | `LLM_BURST_ENABLED=false` (default) |
| **Emergency** | `LLM_BACKEND=openai` + stop burst endpoint (ADR 0004 rollback) |

Helm: burst flags off in all committed overlays until Phase 7 live burst.

## Consequences

- **Positive:** Clear migration from single-cloud GKE to optional burst without rewriting agent logic.
- **Negative:** Live multi-cloud still needs networking, identity, and cost reconciliation work.
- **Supersedes nothing;** extends ADR 0004/0009 with burst policy layer.

## References

- Simulation: `apps/llm_burst_routing.py`, `scripts/simulate_multicloud_burst_routing.py`
- Runbook: [multicloud_burst_routing.md](../runbooks/multicloud_burst_routing.md)
- [02-production-scale.md](../../roadmap/02-production-scale.md) — Stage 4 multi-cloud burst
