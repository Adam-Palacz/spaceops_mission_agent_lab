# LLM backend rollout runbook (PS5.5)

This runbook explains how to roll out `LLM_BACKEND=gpu` safely and how to rollback without deploying code.

## Canonical config model

- Routing knob: `LLM_BACKEND=openai|cursor_sh|gpu`
- Deprecated compatibility only: `LLM_PROVIDER=openai|cursor_sh` (used only when `LLM_BACKEND` is unset)
- Safe default when unset: `openai`

## Environment policy

- **dev**: default `openai`; use `gpu` only for smoke/canary runs.
- **stage**: optional GPU canary on one worker, baseline remains `openai`.
- **prod**: controlled canary rollout; emergency baseline is always `openai`.

## GPU canary checklist

1. Start GPU runtime:
   - `make gpu-up`
2. Verify readiness + one call:
   - `python scripts/llm_gpu_smoke.py --health-only --generate`
3. Enable canary:
   - set `LLM_BACKEND=gpu` on one worker/process
4. Observe:
   - gateway logs: `backend_requested`, `backend_actual`, `fallback_used`, `fallback_reason`
   - metric: `llm_backend_fallback_total{from_backend="gpu",to_backend="openai",reason=...}`
5. Expand rollout only if fallback pressure is low and quality gates pass.

## Emergency rollback (no code deploy)

**Compose / Makefile path:**

1. Switch config to `LLM_BACKEND=openai`
2. Stop GPU runtime:
   - `make gpu-down`
3. Validate new calls show `backend_actual=openai`.

**Kubernetes / Helm path:** see [k8s_rollout_rollback.md § LLM emergency rollback](k8s_rollout_rollback.md#llm-emergency-rollback-ps55-on-k8s) — patch `api.llm.backend=openai`, disable NIM profile, `kubectl rollout restart` if needed.

## Failure interpretation

- `backend_requested=gpu`, `backend_actual=gpu`: GPU serving.
- `backend_requested=gpu`, `backend_actual=openai`, `fallback_used=true`: resilience fallback active.
- Repeated fallback indicates GPU instability or bad capacity.

For fallback triage details see:
- `docs/runbooks/llm_backend_fallback.md`

## Notes

- CI default should remain GPU-free. Optional GPU smoke stays manual (`workflow_dispatch`).
- Budget guardrail (`LLMBudgetExceededError`) is not a fallback condition.
- In parity (PS5.8), GPU arm is invalid when fallback occurs.

## Kubernetes / GitOps path (PS6)

Per [ADR 0005](../adr/0005-environment-strategy-dev-stage-prod.md):

- Set `LLM_BACKEND` in Helm **values overlay** (`values-dev.yaml`, `values-stage.yaml`, `values-prod.yaml`) — not `LLM_PROVIDER`.
- Stage GPU canary: change values + rolling restart; attach PS5.8 parity report when promoting GPU.
- Emergency rollback: patch values to `LLM_BACKEND=openai`, redeploy or restart affected Deployment; disable NIM Helm profile if enabled.

Full K8s deploy/rollback procedures: [k8s_rollout_rollback.md](k8s_rollout_rollback.md).
