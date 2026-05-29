# PS5 — Sprint review

**Sprint:** Production Scale — Sprint 5 (PS5.1–PS5.8)  
**Board:** [BOARD.md](BOARD.md) — **8 / 8 Done**  
**Date:** 2026-05-29 (review; PS5.8 manual parity + provenance fix)

---

## Executive summary

PS5 delivered **LLM backend portability with optional GPU off by default**: a hardened gateway
(`LLM_BACKEND=openai|cursor_sh|gpu`), OpenAI and NIM adapters, explicit fallback metadata (PS5.4),
rollout/cost guardrails (PS5.5–PS5.6), host-run idle scale-to-zero (PS5.7), and a **backend parity
promotion signal** (PS5.8) that rejects GPU evidence when fallback or mixed backends occurred.

Sprint goal from [README.md](README.md) is **met**. Default PR CI stays **GPU-free**; GPU smoke is
manual / self-hosted-runner oriented, and backend parity runs fixture tests plus optional live arms
via `workflow_dispatch` / schedule. Manual PS5.8 acceptance records NIM-up promotion
(`gpu_promotion: allowed`) and NIM-down blocking (`invalid_fallback`, no false comparable match);
the generated reports are local gitignored operator artifacts, not committed repo evidence.

---

## Goals vs outcomes

| README outcome | Status |
|----------------|--------|
| Unified gateway: `openai`, `cursor_sh`, optional `gpu` (NIM) | Done (PS5.1, PS5.3) |
| Health checks, circuit breaker, fallback with explicit metadata | Done (PS5.4) |
| Cost guardrails (`LLM_BUDGET_MODE` process vs postgres) | Done (PS5.6) |
| Host-run idle TTL + `last_gpu_call_at` activity signal | Done (PS5.7) |
| Parity evals invalid on fallback / invalid OpenAI baseline | Done (PS5.8) |

---

## Board summary

| Task | Status |
|------|--------|
| PS5.1 Gateway backend abstraction | Done |
| PS5.2 OpenAI adapter parity tests | Done |
| PS5.3 Optional GPU backend (NIM) | Done |
| PS5.4 Healthcheck + circuit breaker | Done |
| PS5.5 Feature flags + rollout policy | Done |
| PS5.6 Cost telemetry + guardrails | Done |
| PS5.7 Idle TTL scale-to-zero | Done |
| PS5.8 Parity eval suite + tolerance | Done |

---

## Definition of Done (sprint checklist)

1. **`LLM_BACKEND=openai|cursor_sh|gpu` through one gateway** — PS5.1/PS5.5; `docs/llm_gateway.md`.
2. **`LLM_BACKEND=gpu` proven with NIM** — manual smoke (PS5.3); `scripts/llm_gpu_smoke.py`, compose profile `gpu`.
3. **GPU outage → OpenAI fallback with metadata** — PS5.4; `fallback_used`, `fallback_reason`; no silent swap.
4. **Budget exceed → escalation, not fallback** — PS5.6; `LLMBudgetExceededError` / `budget_exceeded`.
5. **Idle shutdown + activity file on host** — PS5.7; `./var:/app/var`, `gpu_idle_shutdown.*`, runbook.
6. **Parity promotion requires valid openai+gpu pairs** — PS5.8; fixture tests + manual NIM up/down reports.
7. **Tracing SaaS = trend only** — documented in PS5.8 / `docs/evals_backend_parity.md`; not a merge gate.

---

## What shipped (by theme)

- **PS5.1** — `resolve_llm_backend()`, normalized `generate()` metadata (`backend_requested`, `backend_actual`, …).
- **PS5.2** — OpenAI adapter contract tests; reference cloud arm.
- **PS5.3** — NIM compose profile (off by default), `make gpu-up` / `gpu-down`, `docs/llm_gpu_backend.md`, `gpu-smoke.yml`.
- **PS5.4** — NIM health preflight, circuit breaker, OpenAI fallback; resilience tests separate from parity promotion.
- **PS5.5** — [ADR 0004](../../../docs/adr/0004-llm-backend-rollout.md), [llm_backend_rollout.md](../../../docs/runbooks/llm_backend_rollout.md).
- **PS5.6** — Process/postgres budget modes, cost logging; [llm_cost_guardrails.md](../../../docs/llm_cost_guardrails.md).
- **PS5.7** — `scripts/gpu_idle_shutdown.py` (+ sh/ps1), `make gpu-idle-check`, [gpu_cost_hygiene.md](../../../docs/runbooks/gpu_cost_hygiene.md).
- **PS5.8** — `evals/backend_parity.py`, `apps/llm_provenance.py`, fixture + live runner, [evals_backend_parity.md](../../../docs/evals_backend_parity.md), `backend-parity.yml`.

---

## Manual / operator evidence (not in default CI)

| Scenario | Command / artifact | Result (2026-05-29) |
|----------|-------------------|---------------------|
| NIM up — parity promotion | `python -m evals.backend_parity --run-both` → local `backend_parity_manual_nim_up.json` | Recorded in PS5.8 acceptance: all 4 arms `comparable`; `gpu_promotion: allowed`; 2 comparisons |
| NIM down — no false match | NIM stopped → same command → local `backend_parity_manual_nim_down.json` | Recorded in PS5.8 acceptance: GPU arms `invalid_fallback`; `comparisons: []`; `gpu_promotion: blocked` |
| Idle TTL dry-run | `make gpu-idle-check` | Unit + operator scripts (PS5.7) |

Reports under `evals/reports/backend_parity_manual_*.json` are gitignored local operator artifacts;
re-run PS5.8 before any real GPU promotion.

---

## Notable fixes during sprint close

- **PS5.8 provenance capture** — `ContextVar` did not propagate into `ThreadPoolExecutor` graph workers (PS1.9); replaced with thread-safe capture stack in `apps/llm_provenance.py`.
- **PS5.7** — `GPU_ACTIVITY_FILE` env override, integration target `make gpu-idle-integration`, explicit pytest skips on Windows.
- **PS5.8 sample report** — removed duplicate `(case_id, backend_arm)` rows; `promotion_blockers` aligned with `merge_parity_report()`.
- **backend-parity.yml** — skip live job without `OPENAI_API_KEY`; MCP cleanup via `trap`; preserve exit code (no `\|\| true`).

---

## CI architecture (PS5 additions)

Default PR CI unchanged — **no GPU containers on merge path** (comment in `ci.yml`).

```text
lint → golden-check → safety-gates → semantic-evals → test → docker-build
                              ↓
                    evals-hard / evals-soft (live, if OPENAI_API_KEY)
                              ↓
                    gate-summary

Off PR path (workflow_dispatch / schedule):
  gpu-smoke.yml      — manual/self-hosted NIM health + generate checklist (PS5.3)
  backend-parity.yml — fixture tests + optional live openai/gpu parity (PS5.8, soft)
  shadow-models.yml  — model promotion (P4.8, unchanged)
```

Soft gate documented: [ci_gating_policy.md](../../../docs/runbooks/ci_gating_policy.md) gate `#12 backend-parity-ps58`.

---

## Risks / carry-forward

| Item | Notes |
|------|--------|
| **GPU hardware** | NIM smoke and parity live arms require local NVIDIA + NGC; not enforced on every PR. |
| **Parity case count** | Only `must-escalate-no-evidence` + `citation-present`; expand before production GPU promotion. |
| **Postgres budget mode** | Documented; full PS6 deploy semantics deferred. |
| **LangSmith / MLflow parity export** | Optional trend only; not implemented as merge gate (by design). |

---

## Recommendation

**Close PS5** for planning and delivery. Phase 5 LLM backend slice is reference-complete for lab use.

**Next:** PS6 — per-environment `LLM_BACKEND` deploy, postgres budget wiring if needed, and cluster
operationalization per [02-production-scale.md](../../02-production-scale.md). Re-run PS5.8 parity
before any production `LLM_BACKEND=gpu` promotion.

---

## Actions captured in repo

- [README.md](README.md) — DoD complete  
- [BOARD.md](BOARD.md) — 8/8 Done  
- [SPRINT_REVIEW.md](SPRINT_REVIEW.md) — this file  
- [PS5.8 spec](PS5.8-parity-eval-suite-tolerance.md) — manual acceptance checked  
