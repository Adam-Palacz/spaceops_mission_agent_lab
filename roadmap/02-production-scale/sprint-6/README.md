# Production Scale — Sprint 6 (PS6)

**Goal:** package the system for platform operations (K8s/GitOps/cloud path) and close portfolio
artifacts for external demonstration and production-readiness review.

---

## Outcomes

- Environment model (`dev/stage/prod`) with documented promotion path.
- K8s local proof with deploy/rollback runbooks and baseline policies.
- Cloud deployment baseline (GCP-first, portable manifests/IaC boundaries).
- Portfolio-grade docs: ADR set, threat model, runbooks, one-page system README.
- **Durable agent workers:** cluster manifests and runbooks acknowledge **PS3.9** checkpointed graph
  workers (resume after rollout/OOM), not only stateless API replicas.

---

## Tasks

See **[BOARD.md](BOARD.md)** for status of PS6.1–PS6.11.

---

## Definition of done (sprint)

- [ ] Local K8s deploy works with safe rollback and documented procedures.
- [ ] Environment isolation controls are defined and tested at least in local/stage form.
- [ ] Cloud baseline deployment path is reproducible and cost-guarded.
- [ ] Portfolio artifact checklist is complete and review-ready.
- [ ] **PS6.11:** checkpoint / graph worker pattern validated in-cluster (or explicit defer with ADR).

---

## Cross-phase

- [Phase README — Cross-cutting](../README.md#cross-cutting-durability-safety-and-evals)
