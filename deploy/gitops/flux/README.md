# Flux GitOps (deferred)

PS6.7 selected **Argo CD** per [ADR 0008](../../../docs/adr/0008-gitops-argocd.md).

Flux v2 remains a valid alternative for Phase 7 (multi-repo, OCI artifacts, GKE fleet). A future
task would add:

- `HelmRelease` + `GitRepository` sources
- Equivalent sync policies (auto stage, manual prod)
- Same Helm chart path and PS6.6 secret refs

No Flux manifests ship in PS6.7 — use `deploy/gitops/argocd/` for the supported path.
