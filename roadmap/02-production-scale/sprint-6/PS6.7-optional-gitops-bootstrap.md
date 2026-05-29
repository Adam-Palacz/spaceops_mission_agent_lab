# PS6.7 — Optional GitOps bootstrap (Argo CD / Flux)

| Field | Value |
|-------|-------|
| **Task ID** | PS6.7 |
| **Status** | Todo |

---

## Description

Optional **GitOps** path for `stage` / `prod`: cluster state driven from Git (manifests + env overlays).
Lab may remain Makefile/Helm imperative; GitOps proves promotion model from PS6.1.

**Sprint decision:** pick **one** of Argo CD or Flux; document the other as deferred.

---

## Requirements

- [ ] Bootstrap guide: install GitOps controller on local/stage cluster.
- [ ] App-of-apps or equivalent: deploy SpaceOps chart from PS6.2 with env overlay.
- [ ] Sync policy documented: manual vs auto; **prod** requires manual sync or approval (PS6.1).
- [ ] Rollback = Git revert + sync (cross-link PS6.4).
- [ ] Secrets: integrate with PS6.6 (SOPS/ESO); no plain secrets in Application spec.
- [ ] Drift detection: what happens if someone `kubectl edit` (document remediation).

---

## Dependencies

- **PS6.2** — chart source and values paths.
- **PS6.4** — rollback semantics.
- **PS6.1** — promotion gates.

---

## Checklist

- [ ] `docs/runbooks/gitops_bootstrap.md`
- [ ] Example Application/Kustomization manifests in repo.
- [ ] Optional CI: validate Application YAML schema.

---

## Test / acceptance

- [ ] Local/stage: Git commit changes image tag → sync → rollout observed.
- [ ] Rollback via Git revert demonstrated once.
- [ ] Task marked **optional** — PS6 DoD does not require GitOps if ADR defers with rationale.

---

## Deliverables (expected)

- `deploy/gitops/` (Argo or Flux manifests)
- `docs/runbooks/gitops_bootstrap.md`

---

## Out of scope

- Multi-repo app-of-apps for unrelated teams.
- GitOps for GPU node pool autoscaling (Phase 7).
