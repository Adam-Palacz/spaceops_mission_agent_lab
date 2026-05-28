# PS5.5 — Backend feature flags and rollout policy

| Field | Value |
|-------|-------|
| **Task ID** | PS5.5 |
| **Status** | Done |

---

## Description

Define how **`LLM_BACKEND`** is set per environment, how to roll out GPU (NIM) safely, and what the
**safe default** is everywhere (`openai`). Includes GitOps/config layering notes for PS6.

**Authoritative configuration model** is defined in [PS5.1](PS5.1-gateway-backend-abstraction-hardening.md#configuration-model-canonical--ps51--ps55) — this task owns rollout docs and tests, not a second competing schema.

---

## Requirements

- [x] Canonical env: `LLM_BACKEND=openai|cursor_sh|gpu` (see PS5.1 precedence with deprecated `LLM_PROVIDER`).
- [x] Default **`openai`** when unset and no legacy provider-only config.
- [x] Per-environment matrix: `dev` (openai), `stage` (optional gpu canary), `prod` (policy).
- [x] Rollout checklist: `make gpu-up` → NIM smoke (PS5.3) → `LLM_BACKEND=gpu` on one worker → monitor `llm_backend_fallback_total`.
- [x] Emergency rollback: `LLM_BACKEND=openai` + `make gpu-down` — no code deploy required.
- [x] ADR documents migration timeline for removing `LLM_PROVIDER`-only configs.

---

## Dependencies

- **PS5.1–PS5.4** — backends, metadata, fallback behavior.

---

## Checklist

- [x] `.env.example` and `config.py` Field descriptions match PS5.1 table.
- [x] `docs/adr/0004-llm-backend-rollout.md` — NIM opt-in, `LLM_PROVIDER` deprecation.
- [x] CI: default workflow does **not** require GPU; `gpu-smoke` workflow_dispatch only.
- [x] Cross-link `docs/runbooks/ci_gating_policy.md` — parity invalid on fallback (PS5.8).

---

## Test / acceptance

- [x] Test: unknown `LLM_BACKEND` raises clear error.
- [x] Test: unset → `openai`.
- [x] Test: `LLM_PROVIDER=cursor_sh` only → routes as `cursor_sh` + deprecation warning.
- [x] Test: conflicting `LLM_BACKEND=gpu` + `LLM_PROVIDER=cursor_sh` → GPU wins for routing.
- [x] Reviewer can answer “fork PR without GPU?” from docs alone.

---

## Deliverables (expected)

- `docs/adr/0004-llm-backend-rollout.md`
- `docs/runbooks/llm_backend_rollout.md`
- `tests/test_llm_backend_config_ps55.py`
