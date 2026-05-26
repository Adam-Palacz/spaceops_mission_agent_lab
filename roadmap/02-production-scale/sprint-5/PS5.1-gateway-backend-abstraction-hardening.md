# PS5.1 — Gateway backend abstraction hardening

| Field | Value |
|-------|-------|
| **Task ID** | PS5.1 |
| **Status** | Done |

---

## Description

Harden the PS1.6 LLM gateway so **all** agent model traffic flows through one stable contract and
backend selection is explicit, testable, and swappable. PS5 adds optional **`gpu`** routing while
preserving **`cursor_sh`** via a documented two-knob configuration model (see below).

---

## Configuration model (canonical — PS5.1 + PS5.5)

| Knob | Env | Values | Role |
|------|-----|--------|------|
| **Backend (routing)** | `LLM_BACKEND` / `llm_backend` | `openai` \| `cursor_sh` \| `gpu` | Where HTTP traffic is sent |
| **Legacy alias** | `LLM_PROVIDER` / `llm_provider` | `openai` \| `cursor_sh` | **Deprecated**; kept for backward compatibility |

**Precedence**

1. If `LLM_BACKEND` is set → use it; ignore `LLM_PROVIDER` for routing (log one-time deprecation notice if `LLM_PROVIDER` also set).
2. If only `LLM_PROVIDER` is set → map to `LLM_BACKEND` with the same value (`openai` or `cursor_sh`); emit deprecation warning.
3. If neither set → `LLM_BACKEND=openai`.

**Per-backend credentials**

| `LLM_BACKEND` | Credentials / URL |
|---------------|-------------------|
| `openai` | `OPENAI_API_KEY`, `OPENAI_BASE_URL` |
| `cursor_sh` | `CURSOR_SH_API_KEY`, `CURSOR_SH_BASE_URL` |
| `gpu` | `GPU_LLM_BASE_URL`, `GPU_LLM_MODEL_ID` (NIM); `LLM_PROVIDER` **not** used |

**Response metadata (all backends)** — extend normalized `generate()` result:

- `backend_requested` — value of `LLM_BACKEND` after precedence resolution
- `backend_actual` — adapter that served the call (`openai`, `cursor_sh`, `gpu`, or `openai` after fallback)
- `fallback_used` — bool
- `fallback_reason` — str, empty when no fallback

PS5.8 parity and PS5.4 resilience **require** these fields on **every** `generate()` call.

**Parity aggregation:** PS5.8 collects a per-run `llm_calls_provenance` list; case-arm
`valid_for_parity=false` if **any** call used fallback or mixed `backend_actual` (see PS5.8).

---

## Requirements

- [x] Single public entry point remains `generate()` (optional `trace_context: dict | None = None` for OTel/log correlation — **not** required on every caller in PS5.2).
- [x] Backend registry maps resolved `LLM_BACKEND` → adapter with uniform success/error types.
- [x] No direct provider HTTP calls from `apps/agent/nodes.py` or eval runners (grep gate in CI or test).
- [x] Normalized response shape: existing fields + `backend_requested`, `backend_actual`, `fallback_used`, `fallback_reason`.
- [x] Gateway errors: `LLMGatewayTimeoutError`, `LLMGatewayProviderError`, **`LLMBudgetExceededError`**
      (budget deny — no fallback; nodes → `budget_exceeded`).
- [x] Backward-compat test: `LLM_PROVIDER=cursor_sh` only (no `LLM_BACKEND`) routes like `LLM_BACKEND=cursor_sh`.

---

## Dependencies

- **PS1.6** (done): baseline gateway and `docs/llm_gateway.md`.
- **PS5.3–PS5.5** consume the registry; land PS5.1 before adapter-specific work.

---

## Checklist

- [x] Introduce backend protocol or small adapter module (`apps/llm_backends/` or equivalent).
- [x] Migrate `_provider_config()` into registry; implement precedence table above.
- [x] Centralize URL normalization and auth header construction per backend.
- [x] Update `docs/llm_gateway.md` with configuration table and migration from `LLM_PROVIDER`.

---

## Test / acceptance

- [x] Existing `tests/test_llm_gateway.py` pass unchanged or updated for registry layout.
- [x] New test: unsupported `LLM_BACKEND` → clear `LLMGatewayProviderError`.
- [x] New test: `LLM_PROVIDER=cursor_sh` only → `backend_actual=cursor_sh`, deprecation logged once.
- [x] New test: `LLM_BACKEND=gpu` + `LLM_PROVIDER=cursor_sh` → GPU routing, provider ignored.
- [x] Agent e2e path still escalates on gateway timeout (no regression vs PS1.6).

---

## Deliverables (expected)

- `apps/llm_gateway.py` — thin facade over registry
- `apps/llm_backends/*` (or equivalent) — per-backend adapters
- `config.py` — `llm_backend` with precedence helper; `.env.example` migration notes
- `docs/llm_gateway.md` — configuration model + response metadata
- `tests/test_llm_gateway_ps51.py` (or extend existing gateway tests)
