# GitOps manifests (PS6.7)

Optional **Argo CD** bootstrap per [ADR 0008](../../docs/adr/0008-gitops-argocd.md).

| Path | Purpose |
|------|---------|
| [argocd/](argocd/) | AppProject, app-of-apps, per-env Applications |
| [flux/README.md](flux/README.md) | Flux deferred (Phase 7) |

**Quick start (stage cluster or kind with Git remote):**

```bash
make gitops-install      # Argo CD in namespace argocd
make gitops-bootstrap    # AppProject + Applications
make gitops-status
```

Runbook: [docs/runbooks/gitops_bootstrap.md](../../docs/runbooks/gitops_bootstrap.md)

Imperative dev default remains `make k8s-up` — GitOps is **optional** for PS6 DoD.
