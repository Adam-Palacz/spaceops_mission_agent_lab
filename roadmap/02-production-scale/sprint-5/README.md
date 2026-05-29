# Production Scale — Sprint 5 (PS5)

**Goal:** complete LLM backend portability through a strict gateway, optional **NVIDIA NIM** GPU
backend, and cost/safety controls so acceleration remains optional and reversible.

**Strategic source:** [Phase 5 — LLM Backends](../../02-production-scale.md#phase-5--llm-backends-vendor-agnostic--optional-gpu-off-by-default).

---

## Configuration model (read first)

| Knob | Values | Role |
|------|--------|------|
| **`LLM_BACKEND`** | `openai` \| `cursor_sh` \| `gpu` | Routing target (canonical) |
| **`LLM_PROVIDER`** | `openai` \| `cursor_sh` | **Deprecated**; used only when `LLM_BACKEND` unset |

Precedence and per-backend credentials: [PS5.1](PS5.1-gateway-backend-abstraction-hardening.md#configuration-model-canonical--ps51--ps55).

Every `generate()` returns `backend_requested`, `backend_actual`, `fallback_used`, `fallback_reason`
(PS5.1). PS5.8 aggregates **`llm_calls_provenance`** per case arm — **any** fallback or mixed
backend in the run invalidates GPU parity, and promotion requires a valid `openai` baseline for
every required `gpu` case. Budget exceed (**PS5.6**) does **not** trigger fallback (**PS5.4**).
Idle TTL uses host-visible **`./var:/app/var`** mount (**PS5.3** / **PS5.7**).

---

## Outcomes

- Unified gateway: `openai`, `cursor_sh`, optional **`gpu`** (NIM, OpenAI-compatible API).
- Health checks, circuit breaker, fallback to `openai` with explicit metadata (not silent).
- Cost guardrails with honest **`process`** vs **`postgres`** budget semantics (PS5.6).
- Host-run idle TTL + mandatory `last_gpu_call_at` activity signal (PS5.7).
- Backend parity evals that cannot pass on GPU fallback or an invalid OpenAI baseline (PS5.8).

---

## Suggested implementation order

1. **PS5.1** — registry, config precedence, response metadata.
2. **PS5.2** — OpenAI adapter + contract tests (`cursor_sh` adapter shares registry pattern).
3. **PS5.3** + **PS5.4** — NIM compose + GPU adapter + health/fallback.
4. **PS5.5** — rollout ADR/runbook + config tests.
5. **PS5.6** + **PS5.7** — cost modes + idle scripts (gateway writes `last_gpu_call_at`).
6. **PS5.8** — parity runner + invalid-arm/baseline promotion rules.

---

## Tasks

See **[BOARD.md](BOARD.md)** for status.

| Task | Spec |
|------|------|
| PS5.1 | [Gateway backend abstraction hardening](PS5.1-gateway-backend-abstraction-hardening.md) |
| PS5.2 | [OpenAI backend adapter parity tests](PS5.2-openai-backend-adapter-parity-tests.md) |
| PS5.3 | [Optional GPU backend adapter (NIM)](PS5.3-optional-gpu-backend-adapter.md) |
| PS5.4 | [Backend healthcheck + circuit breaker](PS5.4-backend-healthcheck-circuit-breaker.md) |
| PS5.5 | [Backend feature flags and rollout policy](PS5.5-backend-feature-flags-rollout-policy.md) |
| PS5.6 | [Cost telemetry and guardrails](PS5.6-cost-telemetry-guardrails.md) |
| PS5.7 | [Idle TTL and scale-to-zero workflow](PS5.7-idle-ttl-scale-to-zero.md) |
| PS5.8 | [Parity eval suite and tolerance definition](PS5.8-parity-eval-suite-tolerance.md) |

---

## Definition of done (sprint)

- [x] `LLM_BACKEND=openai|cursor_sh|gpu` works through one gateway contract (PS5.1/PS5.5).
- [x] **`LLM_BACKEND=gpu` proven with NIM:** manual smoke checklist in PS5.3 completed (health + `generate()`, `backend_actual=gpu`).
- [x] GPU outage falls back to `openai` with `fallback_used=true`; incident flow continues (PS5.4).
- [x] Cost guardrails documented with explicit **`LLM_BUDGET_MODE`** semantics (PS5.6).
- [x] Idle shutdown uses mandatory `last_gpu_call_at`; host scripts with bash + PowerShell dry-run (PS5.7).
- [ ] Parity report promotes GPU only for complete case pairs where both `openai` and `gpu` arms
      have `valid_for_parity=true` (PS5.8).
- [ ] **PS5.8** documents optional tracing SaaS as nightly/trend only (not merge gate).

---

## Upstream / downstream

- **Upstream:** PS1.6 gateway; PS4.4/PS4.7 eval policy; PS4.6 metrics.
- **Downstream:** PS6 deploys per-env `LLM_BACKEND`; Phase 7 cloud GPU pools extend NIM pattern.
- **Existing code:** `apps/llm_gateway.py`, `config.py` (`llm_provider`), `docs/llm_gateway.md`, `docs/shadow_models.md`.
