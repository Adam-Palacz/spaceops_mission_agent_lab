# GitOps bootstrap (PS6.7 — optional)

Optional **Argo CD** path for stage/prod. Local dev default remains imperative Helm (`make k8s-up`).

**Decision:** [ADR 0008](../adr/0008-gitops-argocd.md) — Argo CD chosen; Flux deferred.

---

## When to use GitOps

| Environment | Default | GitOps |
|-------------|---------|--------|
| **dev (kind)** | `make k8s-up` | Optional demo (`--include-dev`) |
| **stage** | — | Automated sync recommended |
| **prod** | — | Manual sync after approver (ADR 0005) |

---

## Prerequisites

- Kubernetes cluster with `kubectl` context set (kind stage cluster or shared cluster).
- **Git remote** with this repo pushed (HTTPS URL). Argo CD pulls manifests from Git.
- Secrets pre-provisioned per [k8s_secrets_bootstrap.md](k8s_secrets_bootstrap.md) (PS6.6) — **no secrets in Application YAML**.
- Helm chart at `deploy/helm/spaceops/` (PS6.2).

Set if needed:

```bash
export GITOPS_REPO_URL=https://github.com/YOUR_ORG/spaceops_mission_agent_lab.git
export GITOPS_TARGET_REVISION=main
```

---

## 1. Install Argo CD

```bash
make gitops-install
# or: python scripts/gitops_bootstrap.py install --wait
```

Verify:

```bash
kubectl get pods -n argocd
kubectl port-forward svc/argocd-server -n argocd 8080:443
# UI: https://localhost:8080 (admin / initial password from argocd-initial-admin-secret)
```

---

## 2. Bootstrap AppProject + Applications

**Push** `deploy/gitops/` to your Git remote first, then:

```bash
make gitops-bootstrap
# Optional lab dev Application (manual sync):
# python scripts/gitops_bootstrap.py bootstrap --include-dev
```

This applies:

- `AppProject` `spaceops`
- Root **app-of-apps** `spaceops-root` → renders child Applications from `deploy/gitops/argocd/applications/`
- Child apps: `spaceops-stage`, `spaceops-prod`

Check status:

```bash
make gitops-status
kubectl get applications -n argocd
```

---

## 3. Sync policies

| Application | Automated sync | Self-heal | Notes |
|-------------|----------------|-----------|-------|
| `spaceops-root` | Yes | Yes | Manages child Application CRs |
| `spaceops-stage` | Yes | Yes | Integration env |
| `spaceops-prod` | **No** | **No** | Operator runs manual sync after approval |
| `spaceops-dev` (optional) | No | No | Lab only; prefer `make k8s-up` |

**Prod manual sync:**

```bash
argocd app sync spaceops-prod --grpc-web
# or Argo CD UI → spaceops-prod → Sync
```

---

## 4. Promote image tag (stage)

GitOps-managed pins live in:

- `deploy/helm/spaceops/values-gitops-stage.yaml`
- `deploy/helm/spaceops/values-gitops-prod.yaml`

**No secret values** in these files.

Workflow:

1. Edit `images.api.tag` / `images.mcp.tag` in the GitOps values file.
2. `git commit && git push`
3. Stage auto-syncs (or run demo):

```bash
make gitops-rollout-demo --sync-only   # after push; see script flags
python scripts/gitops_rollout_demo.py --sync-only
```

4. Verify:

```bash
kubectl rollout status deployment/spaceops-api -n spaceops-stage
kubectl get deployment spaceops-api -n spaceops-stage -o jsonpath='{.spec.template.spec.containers[0].image}'
```

---

## 5. Rollback (Git revert + sync)

Same semantics as [k8s_rollout_rollback.md#rollback-flow](k8s_rollout_rollback.md#rollback-flow):

1. `git revert <bad-commit>` (or restore previous tag in `values-gitops-*.yaml`)
2. `git push`
3. **Stage:** auto-sync applies revert.
4. **Prod:** manual `argocd app sync spaceops-prod` after approver sign-off.

Imperative `helm rollback` remains valid for emergencies.

---

## 6. Secrets (PS6.6)

- Applications use chart overlays with `secrets.create: false` and `existingSecret`.
- Bootstrap secrets **before** first sync: [k8s_secrets_bootstrap.md](k8s_secrets_bootstrap.md)
- ESO `ExternalSecret` resources are **not** managed by SpaceOps Applications (install separately).
- SOPS: decrypt at deploy boundary; do not commit `*.dec.yaml`.

Optional dev Application uses `parameters` to disable `secrets.create` — password never in Git.

---

## 7. Drift detection and remediation

**Stage (self-heal on):** manual `kubectl edit deployment/...` is overwritten on next reconcile.

Remediation:

1. Fix desired state in Git (PR).
2. `argocd app sync spaceops-stage` if auto-sync lagging.
3. Emergency: `argocd app diff spaceops-stage` before sync.

**Prod (manual sync):** drift persists until operator syncs. Always run `argocd app diff spaceops-prod` before prod sync.

Disable self-heal temporarily only with change ticket and revert plan.

---

## 8. Flux (deferred)

See [deploy/gitops/flux/README.md](../../deploy/gitops/flux/README.md).

---

## Related

- [environment_promotion.md](environment_promotion.md)
- [k8s_rollout_rollback.md](k8s_rollout_rollback.md)
- [local_k8s_dev.md](local_k8s_dev.md) — imperative dev default
- Manifests: [deploy/gitops/](../../deploy/gitops/)
