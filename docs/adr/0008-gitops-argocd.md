# ADR 0008 — GitOps controller (Argo CD)

- **Status:** Accepted
- **Date:** 2026-05-29
- **Related:** PS6.7, [ADR 0005](0005-environment-strategy-dev-stage-prod.md), [ADR 0006](0006-kubernetes-packaging-helm.md), [ADR 0007](0007-secrets-management-k8s.md), [PS6.4 runbook](../runbooks/k8s_rollout_rollback.md)

## Context

PS6.2 packages SpaceOps as Helm; PS6.4 documents imperative rollout/rollback. PS6.1 requires a
**promotion model** where stage/prod cluster state is traceable to Git. PS6.7 adds an **optional**
GitOps path — sprint DoD does not require every engineer to run Argo CD locally.

We must pick **one** of Argo CD or Flux and document the other as deferred.

## Decision

### 1. Controller: **Argo CD** (Flux deferred)

| | **Argo CD (chosen)** | **Flux (deferred)** |
|---|---------------------|---------------------|
| Helm native Application CR | Yes (`Application` with `helm` source) | HelmRelease CR |
| UI + manual sync for prod | Built-in | Requires Flagger/others for similar UX |
| App-of-apps | Root `Application` → Helm-rendered `applications/` folder | Flux Kustomization hierarchy |
| PS6.7 scope fit | Good for portfolio demo + stage auto-sync | Valid; revisit Phase 7 multi-repo |

Flux remains a documented alternative in `deploy/gitops/flux/README.md` — no manifests shipped in PS6.7.

### 2. Scope by environment

| Environment | GitOps | Sync policy |
|-------------|--------|-------------|
| **dev (local kind)** | Optional — `make k8s-up` imperative default | Manual / demo only |
| **stage** | Recommended | **Automated** sync + self-heal |
| **prod** | Required path when GitOps enabled | **Manual** sync only (ADR 0005 approver gate) |

Lab engineers may keep Makefile/Helm; stage/prod prove promotion from Git.

### 3. Source layout

- Manifests: `deploy/gitops/argocd/`
- Helm chart unchanged: `deploy/helm/spaceops/` (PS6.2)
- GitOps-managed image pins: `deploy/helm/spaceops/values-gitops-{stage,prod}.yaml` (no secrets)
- App-of-apps: root `Application` → small Helm chart that renders child Applications per env

`Application.spec.source.repoURL` must point at this repository (HTTPS). Bootstrap script substitutes
`__GITOPS_REPO_URL__` from `git remote get-url origin` or `GITOPS_REPO_URL`; the root Application
passes that value into the child-Application chart as `repoUrl`.

### 4. Secrets (PS6.6)

- **No** plaintext secrets in `Application` specs or GitOps value files.
- Stage/prod Applications use chart overlays with `secrets.create: false` and `existingSecret` (ESO/SOPS).
- Argo CD does not decrypt SOPS by default; ESO syncs Secrets independently (documented in runbook).

### 5. Rollback

Same semantics as PS6.4:

1. `git revert` the commit that changed `values-gitops-*.yaml` or env overlay.
2. **Stage:** auto-sync applies revert.
3. **Prod:** operator triggers manual sync in Argo CD UI/CLI after approver sign-off.

Imperative `helm rollback` remains valid for incidents; GitOps is the promotion path.

### 6. Drift

With **self-heal** enabled (stage), manual `kubectl edit` is reverted on next sync. Remediation:

- Prefer Git PR → sync.
- Emergency: `argocd app sync spaceops-stage --force` after Git fix, or disable self-heal temporarily (documented).

Prod (manual sync): drift persists until operator syncs; use `argocd app diff` before sync.

## Consequences

- **Positive:** Promotion auditable in Git; aligns with PS6.1/PS6.4; optional for local dev.
- **Negative:** Requires cluster access to Git remote (not pure offline kind without push).
- **Follow-up:** Phase 7 may add Flux for multi-tenant repos or GKE fleet patterns.

## References

- `deploy/gitops/argocd/`
- `docs/runbooks/gitops_bootstrap.md`
- Deferred: `deploy/gitops/flux/README.md`
