# PS6.7 — Optional GitOps bootstrap (Argo CD / Flux)

| Field | Value |
|-------|-------|
| **Task ID** | PS6.7 |
| **Status** | Done |

---

## Description

Optional **GitOps** path for `stage` / `prod`: cluster state driven from Git (manifests + env overlays).
Lab may remain Makefile/Helm imperative; GitOps proves promotion model from PS6.1.

**Sprint decision:** **Argo CD** chosen; Flux documented as deferred ([ADR 0008](../../../docs/adr/0008-gitops-argocd.md)).

---

## Requirements

- [x] Bootstrap guide: install GitOps controller on local/stage cluster.
- [x] App-of-apps or equivalent: deploy SpaceOps chart from PS6.2 with env overlay.
- [x] Sync policy documented: manual vs auto; **prod** requires manual sync or approval (PS6.1).
- [x] Rollback = Git revert + sync (cross-link [PS6.4 k8s_rollout_rollback.md](../../../docs/runbooks/k8s_rollout_rollback.md#rollback-flow)).
- [x] Secrets: integrate with PS6.6 (SOPS/ESO); no plain secrets in Application spec.
- [x] Drift detection: what happens if someone `kubectl edit` (document remediation).

---

## Dependencies

- **PS6.2** — chart source and values paths.
- **PS6.4** — rollback semantics.
- **PS6.1** — promotion gates.

---

## Checklist

- [x] `docs/runbooks/gitops_bootstrap.md`
- [x] Example Application/Kustomization manifests in repo.
- [x] Optional CI: validate Application YAML schema.

---

## Test / acceptance

- [x] Local/stage: Git commit changes image tag → sync → rollout observed (documented + `gitops-rollout-demo`).
- [x] Rollback via Git revert demonstrated once (runbook + PS6.4 cross-link).
- [x] Task marked **optional** — PS6 DoD does not require GitOps if ADR defers with rationale.

---

## Deliverables (expected)

- `deploy/gitops/` (Argo CD manifests)
- `docs/runbooks/gitops_bootstrap.md`

---

## Out of scope

- Multi-repo app-of-apps for unrelated teams.
- GitOps for GPU node pool autoscaling (Phase 7).
