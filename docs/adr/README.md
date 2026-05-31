# Architecture Decision Records (ADRs)

Short-lived decisions live in roadmap task specs; **cross-cutting choices** that affect multiple sprints live here.

ADR entries are **append-only**: superseded documents keep full text; status updates point forward — same spirit as JetStream logs.

| ADR | Title | Status |
|-----|-------|--------|
| [0001-queue-strategy-postgres-first-jetstream-later.md](0001-queue-strategy-postgres-first-jetstream-later.md) | Queue / Postgres-first lab path (PS3.1 v1) | **Superseded** |
| [0002-ingest-nats-first-postgres-evidence-store.md](0002-ingest-nats-first-postgres-evidence-store.md) | **Ingest NATS-first; Postgres evidence store** | **Accepted** |
| [0003-langgraph-durable-checkpoint-postgres.md](0003-langgraph-durable-checkpoint-postgres.md) | **Durable agent checkpoint in Postgres** | **Accepted** |
| [0004-llm-backend-rollout.md](0004-llm-backend-rollout.md) | **LLM backend rollout policy (`LLM_BACKEND`)** | **Accepted** |
| [0005-environment-strategy-dev-stage-prod.md](0005-environment-strategy-dev-stage-prod.md) | **Environment strategy (`dev` / `stage` / `prod`)** | **Accepted** |
| [0006-kubernetes-packaging-helm.md](0006-kubernetes-packaging-helm.md) | **Kubernetes packaging (Helm)** | **Accepted** |
| [0007-secrets-management-k8s.md](0007-secrets-management-k8s.md) | **Kubernetes secrets (SOPS / External Secrets)** | **Accepted** |
| [0008-gitops-argocd.md](0008-gitops-argocd.md) | **GitOps controller (Argo CD; Flux deferred)** | **Accepted** |

**Current ingest / queue strategy:** read **ADR 0002** first.
