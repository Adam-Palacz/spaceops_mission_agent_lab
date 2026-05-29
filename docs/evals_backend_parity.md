# Backend parity evals (PS5.8)

Compare **`LLM_BACKEND=openai`** vs **`LLM_BACKEND=gpu`** (NVIDIA NIM) within documented
tolerances. Parity is a **promotion / nightly signal** — it does **not** replace deterministic
`semantic-evals` or `evals-hard` merge gates (PS4.7).

Resilience behaviour (PS5.4 fallback, circuit breaker) is tested separately; a GPU arm that
falls back to OpenAI is **not** valid parity evidence.

## When to run

- **Before promoting** `LLM_BACKEND=gpu` in an environment (after PS5.5 rollout checklist).
- **Nightly / on demand** via `.github/workflows/backend-parity.yml` (soft gate).
- **Locally** when NIM is up and `OPENAI_API_KEY` is configured.

Default PR CI stays GPU-free; fixture unit tests run in `pytest tests/test_backend_parity_ps58.py`.

## How to run locally

```bash
# Both arms + merged report (needs live LLM + NIM for gpu arm)
python -m evals.backend_parity --run-both --write-report evals/reports/backend_parity_latest.json

# One arm at a time
python -m evals.backend_parity --backend openai --write-arm evals/reports/arm_openai.json
python -m evals.backend_parity --backend gpu --write-arm evals/reports/arm_gpu.json
python -m evals.backend_parity --merge evals/reports/arm_openai.json evals/reports/arm_gpu.json \
  --write-report evals/reports/backend_parity_merged.json

# Non-blocking signal (exit 0 even when promotion blocked)
python -m evals.backend_parity --run-both --soft-signal
```

Start Telemetry MCP if cases need it (same as `evals.scoring`).

**Cases:** `must-escalate-no-evidence`, `citation-present` from `evals/cases.yaml`.

## Provenance collection

The runner activates `apps.llm_provenance.capture_llm_provenance()` during each case run.
Gateway metadata (`backend_requested`, `backend_actual`, `fallback_used`, …) is read from
the harness — **not inferred from env alone**.

## Parity status (case-arm level)

Fixed priority (see PS5.8 spec):

| Priority | `parity_status` | Meaning |
|----------|-----------------|---------|
| 1 | `invalid_mixed_backends` | More than one `backend_actual` in the arm |
| 2 | `invalid_fallback` | Any call with `fallback_used=true` (single actual) |
| 3 | `invalid_gpu_unavailable` | GPU arm never served NIM |
| 4 | `invalid_backend_mismatch` | OpenAI arm served non-openai adapter |
| 5 | `comparable` | All calls match `backend_arm`, no fallback |

`valid_for_parity = (parity_status == "comparable")`.

## Promotion vs resilience

| Signal | Blocks PR merge? | Blocks GPU promotion? |
|--------|------------------|------------------------|
| PS5.4 resilience tests | No (pytest) | No |
| PS5.8 parity report | No (soft workflow) | **Yes** when `gpu_promotion: blocked` |
| `evals-hard` / `semantic-evals` | **Yes** | N/A |

**Promotion rule:** every required case pair must have both `openai` and `gpu` arms with
`valid_for_parity=true`. Blocked when:

- GPU arm: `invalid_fallback`, `invalid_mixed_backends`, or `invalid_gpu_unavailable`
- OpenAI arm: `invalid_backend_mismatch`
- Either required arm is missing

Aggregate comparison (escalation match, citation presence) runs **only** on comparable pairs.
Others appear in `excluded_from_comparison` with offending `call_index` values.

## Tolerances {#tolerances}

### Exact match (parity comparison)

- **Escalation yes/no** — `escalated` must match between arms for `must-escalate` cases.
- **Policy deny / audit semantics** — covered by deterministic `semantic-evals` (hard gate).

### Allowed drift (informational in parity report)

- **Wording** — report text, plan phrasing, subsystem label when still within eval scoring pass.
- **Latency** — report includes `latency_drift_ms`; p95 band is **trend-only** (not merge gate).
  Suggested band for manual review: GPU within **2×** OpenAI wall time on the same case.

Parity does **not** assert token-level or embedding similarity.

## Report schema

Static example (all invalid statuses + comparable):  
[evals/reports/sample_backend_parity_report.json](../evals/reports/sample_backend_parity_report.json)

Generated reports: `evals/reports/backend_parity_*.json` (gitignored).

## Optional tracing export

LangSmith / MLflow export for trend dashboards is **out of scope** for merge gates. Use nightly
artifacts or external tooling if needed; fixture evals remain authoritative for CI.

## Related

- Implementation: [`evals/backend_parity.py`](../evals/backend_parity.py)
- Gateway metadata: [`docs/llm_gateway.md`](llm_gateway.md)
- GPU rollout: [`docs/runbooks/llm_backend_rollout.md`](runbooks/llm_backend_rollout.md)
- CI policy: [`docs/runbooks/ci_gating_policy.md`](runbooks/ci_gating_policy.md)
- Spec: [PS5.8](../roadmap/02-production-scale/sprint-5/PS5.8-parity-eval-suite-tolerance.md)
