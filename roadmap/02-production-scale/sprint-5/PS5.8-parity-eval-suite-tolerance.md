# PS5.8 — Parity eval suite and tolerance definition

| Field | Value |
|-------|-------|
| **Task ID** | PS5.8 |
| **Status** | Done |

---

## Description

Compare **`LLM_BACKEND=openai`** vs **`LLM_BACKEND=gpu`** (NIM) within documented tolerances.
**Deterministic YAML gates remain merge blockers** — parity is a **promotion / nightly** signal
(PS4.7), not a substitute for `semantic-evals` or `evals-hard`.

**Anti-false-positive rule:** if the GPU arm used **fallback to OpenAI**, that arm is
**not** valid evidence of GPU parity.

---

## Parity report schema

### Per `generate()` call (from PS5.1)

Each LLM invocation appends one entry to **`llm_calls_provenance`** for that eval run / case arm:

| Field | Description |
|-------|-------------|
| `call_index` | 0-based order within the run |
| `node` | e.g. `triage`, `decide`, `report` |
| `backend_requested` | Config for this call |
| `backend_actual` | Adapter that served the call |
| `fallback_used` | bool |
| `fallback_reason` | str |

### Per case arm (aggregated — one row per `case_id` + backend arm)

| Field | Description |
|-------|-------------|
| `case_id` | Eval case identifier |
| `backend_arm` | `openai` or `gpu` (requested backend for this parity run) |
| `llm_calls_provenance` | List of per-call records (above) |
| `valid_for_parity` | See aggregation rule below |
| `parity_status` | `comparable` \| `invalid_fallback` \| `invalid_mixed_backends` \| `invalid_gpu_unavailable` \| `invalid_backend_mismatch` |

### Run-level aggregation rule (multi-call workflows)

Agent/eval runs often call `generate()` **more than once** (triage + decide + report). Parity is
judged at **case-arm** level, not per isolated call.

**`parity_status` derivation (fixed priority — implement exactly):**

1. If `len({c.backend_actual for c in llm_calls_provenance}) > 1` → **`invalid_mixed_backends`**
   (e.g. call 0 `gpu`, call 1 `openai` after fallback — mixed execution in one arm).
2. Else if **any** `c.fallback_used` → **`invalid_fallback`**
   (all calls share one `backend_actual`, but at least one used fallback — e.g. single-call GPU arm
   that fell back to OpenAI only).
3. Else if `backend_arm == "gpu"` and not all `backend_actual == "gpu"` → **`invalid_gpu_unavailable`**
   (GPU arm never served NIM — e.g. all calls `openai` without `fallback_used` recorded, or GPU down).
4. Else if `backend_arm == "openai"` and not all `backend_actual == "openai"` → **`invalid_backend_mismatch`**
   (OpenAI arm served a different adapter, e.g. `cursor_sh` — configuration or harness bug).
5. Else if all calls match `backend_arm` with no fallback → **`comparable`** (`valid_for_parity=true`).

**No catch-all:** if provenance is empty, fields are missing, or `backend_arm` is invalid, the parity
runner **raises `ParityRunnerError`**, fails the job, and does **not** emit a `gpu_promotion` verdict
(schema/harness fault — not a parity outcome).

`valid_for_parity` is **`true` only when `parity_status == comparable`**.

```
valid_for_parity = (parity_status == "comparable")
```

**Promotion rule:** GPU backend may be promoted only if **every required case pair** has both
an `openai` arm and a `gpu` arm with `valid_for_parity=true` (`parity_status == comparable`).
Promotion is blocked if any required GPU-arm row has `valid_for_parity=false`, including:

- `invalid_fallback`
- `invalid_mixed_backends`
- `invalid_gpu_unavailable`

Promotion is also blocked if a required OpenAI baseline arm has
`parity_status=invalid_backend_mismatch`, or if either required arm is missing. A valid GPU result
without a valid OpenAI baseline is not parity evidence.

Set `gpu_promotion: blocked` with the list of offending `case_id`, `backend_arm`, and
`parity_status`. Resilience tests (PS5.4) still pass independently of parity promotion.

Aggregate comparison (escalation match, citation presence) runs **only** on case pairs where
**both** arms have `valid_for_parity=true`. Others go to `excluded_from_comparison` with
`parity_status` and offending `call_index` values.

---

## Requirements

- [x] Tolerance doc: exact match (escalation yes/no, policy deny) vs allowed drift (wording, latency p95 band).
- [x] Parity runner: two explicit runs — `LLM_BACKEND=openai` and `LLM_BACKEND=gpu` — merge by case id.
- [x] Runner reads gateway metadata from eval harness (or structured log tail) — not inference from env alone.
- [x] CI: `.github/workflows/backend-parity.yml` — `workflow_dispatch` + schedule; **soft** gate (PS4.7).
- [x] Optional LangSmith/MLflow export for trends — does not replace fixture evals.
- [x] Sample report: `evals/reports/sample_backend_parity_report.json` includes examples for
      `invalid_fallback`, `invalid_mixed_backends`, `invalid_gpu_unavailable`, and
      `invalid_backend_mismatch` (multi-entry `llm_calls_provenance` where applicable).

---

## Dependencies

- **PS5.1** — metadata on every `generate()`.
- **PS5.3** — NIM smoke proves GPU arm can achieve `valid_for_parity=true` in manual run.
- **PS5.4** — fallback behavior tested separately from parity promotion.
- **PS4.4 / PS4.7** (done).

---

## Checklist

- [x] `evals/backend_parity.py` — `--backend openai|gpu`, emits schema above.
- [x] Cases: must-escalate + citation-present (from existing suites).
- [x] `docs/evals_backend_parity.md` — promotion vs resilience distinction.
- [x] Unit test: single-call, `fallback_used=true`, all `backend_actual=openai` →
      `parity_status=invalid_fallback` (not `invalid_mixed_backends`).
- [x] Unit test: **mixed run** — call 0 `backend_actual=gpu`, call 1 `backend_actual=openai`,
      `fallback_used=true` on call 1 → `parity_status=invalid_mixed_backends` (priority 1).
- [x] Unit test: OpenAI baseline arm served only by `cursor_sh`, GPU arm is `comparable` →
      OpenAI arm `parity_status=invalid_backend_mismatch` and `gpu_promotion: blocked`.
- [x] Unit test: required case is missing either arm → `gpu_promotion: blocked`.

---

## Test / acceptance

- [x] Fixture-based CI test: no live LLM; validates schema and `invalid_fallback` handling.
- [ ] Manual (with NIM up): both arms `valid_for_parity=true` on ≥2 cases → `comparable` summary.
- [ ] Manual (with NIM down): GPU arm `invalid_fallback` or `invalid_gpu_unavailable` — **no** false “100% match”.
- [x] `ci_gating_policy.md` updated: parity job is **non-blocking** on PRs; promotion requires
      complete case pairs where both `openai` and `gpu` arms are `comparable`. Any invalid GPU arm
      (`invalid_fallback`, `invalid_mixed_backends`, or `invalid_gpu_unavailable`), an
      `invalid_backend_mismatch` OpenAI baseline, or a missing required arm sets
      `gpu_promotion: blocked` in the parity report (promotion/nightly signal only, not a merge gate).

---

## Deliverables (expected)

- `evals/backend_parity.py`
- `docs/evals_backend_parity.md`
- `evals/reports/sample_backend_parity_report.json`
- `.github/workflows/backend-parity.yml`
- `tests/test_backend_parity_ps58.py`
- Updates to `docs/runbooks/ci_gating_policy.md`
