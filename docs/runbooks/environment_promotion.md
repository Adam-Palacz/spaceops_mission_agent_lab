# Environment promotion (`dev` → `stage` → `prod`)

Operator guide for promoting SpaceOps across environments under [ADR 0005](../adr/0005-environment-strategy-dev-stage-prod.md).

## Environment map

| Environment | Typical runtime | Namespace (K8s) |
|-------------|-----------------|-----------------|
| **dev** | Docker Compose, kind/k3d on laptop | `spaceops-dev` |
| **stage** | Shared cluster integration | `spaceops-stage` |
| **prod** | Shared or dedicated cluster (Phase 7) | `spaceops-prod` |

Local Compose = **dev** semantics (synthetic data, engineer-owned keys in `.env`).

## Configuration layering (K8s)

1. Helm base: `deploy/helm/spaceops/values.yaml`
2. Env overlay: `values-dev.yaml` | `values-stage.yaml` | `values-prod.yaml`
3. Optional profiles: minimal dev, observability, NIM/GPU (off by default)
4. Secrets: External Secrets / SOPS refs only — see PS6.6
5. GitOps (optional PS6.7): stage auto-sync from Git; prod manual sync — [gitops_bootstrap.md](gitops_bootstrap.md)

Do **not** commit secret values. Stage/prod never use laptop `.env` files on nodes.

## Promotion checklist

### Any change → stage

- [ ] Default CI green (unit, integration, manifest lint when PS6.2 ships)
- [ ] `helm template` / deploy dry-run for `values-stage.yaml`
- [ ] Secrets present via PS6.6 path (not plain Git)
- [ ] PS6.5 isolation (RBAC, NetworkPolicy) applied in `spaceops-stage` — [k8s_environment_isolation.md](k8s_environment_isolation.md)

### Fork PR without GPU

Changes that **do not** modify:

- `LLM_BACKEND`, GPU/NIM Helm profile, or GPU-related env vars

…require **CI only**. No PS5.8 parity artifact.

### GPU canary → stage

1. Complete [LLM backend rollout](llm_backend_rollout.md) smoke on target cluster context.
2. Run [backend parity](../evals_backend_parity.md); require `gpu_promotion: allowed`.
3. Set `LLM_BACKEND=gpu` on **one** Deployment or replica set (canary); baseline stays `openai` elsewhere.
4. Monitor gateway logs and `llm_backend_fallback_total`.
5. Roll back with config only: `LLM_BACKEND=openai` + stop NIM profile.

### stage → prod

- [ ] All stage gates above satisfied on current release candidate
- [ ] [Rollout / rollback](k8s_rollout_rollback.md) exercised on stage (PS6.4)
- [ ] Demo scenarios A (report + evidence) and B (escalation) documented and rehearsed
- [ ] **Manual approver** recorded (name + date in change note or PR)
- [ ] Prod GPU: only with parity artifact + explicit approver; default remains `openai`

## LLM backend by environment (summary)

| Env | Default | GPU |
|-----|---------|-----|
| dev | `openai` | Local smoke / engineer machines only |
| stage | `openai` | Optional canary after parity |
| prod | `openai` | Promotion checklist + approver only |

Details: [ADR 0004](../adr/0004-llm-backend-rollout.md), [ADR 0005](../adr/0005-environment-strategy-dev-stage-prod.md).

## Budget mode

All environments use **`LLM_BUDGET_MODE=process`** for PS6. Shared postgres ledger deferred per ADR 0005.
Do not set `postgres` expecting org-wide enforcement until implemented.

## Checkpoint (PS6.11)

PS6 uses **Variant B (API-only):**

- Enable `AGENT_DURABLE_CHECKPOINT_ENABLED=true` on **api** Deployment in stage for acceptance tests.
- Proof: long run → delete api pod → complete via `POST /runs/resume`.

Worker split (Variant A) optional via `values-checkpoint-variant-a.yaml` (PS7.3); default remains Variant B.

## K8s / GitOps notes

- Deploy with Helm overlays from PS6.2; GitOps (PS6.7) optional.
- GPU node pools and in-cluster NIM: Phase 7 default; not required for PS6 stage/prod baseline.
- Cross-link GPU lab hygiene: [gpu_cost_hygiene.md](gpu_cost_hygiene.md) (Compose) vs `cloud_cost_hygiene.md` (PS6.9, when written).

## Related

- [Secrets plan](../secrets.md)
- [LLM cost guardrails](../llm_cost_guardrails.md)
- [CI gating policy](ci_gating_policy.md)
