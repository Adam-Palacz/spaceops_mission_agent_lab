# Architecture Decision Records (ADRs)

Short-lived decisions live in roadmap task specs; **cross-cutting choices** that affect multiple sprints live here.

ADR entries are **append-only**: superseded documents keep full text; status updates point forward — same spirit as JetStream logs.

**Portfolio index:** [docs/portfolio/README.md](../portfolio/README.md) · **Threat model:** [docs/threat_model.md](../threat_model.md)

---

## Index (0001–0009)

| ADR | Title | Status | Theme | Sprint |
|-----|-------|--------|-------|--------|
| [0001](0001-queue-strategy-postgres-first-jetstream-later.md) | Queue / Postgres-first lab path (PS3.1 v1) | **Superseded** → 0002 | Queue | PS3 |
| [0002](0002-ingest-nats-first-postgres-evidence-store.md) | **Ingest NATS-first; Postgres evidence store** | **Accepted** | Queue / ingest | PS3 |
| [0003](0003-langgraph-durable-checkpoint-postgres.md) | **Durable agent checkpoint in Postgres** | **Accepted** | Checkpoint | PS3 |
| [0004](0004-llm-backend-rollout.md) | **LLM backend rollout policy (`LLM_BACKEND`)** | **Accepted** | LLM gateway / backends | PS5 |
| [0005](0005-environment-strategy-dev-stage-prod.md) | **Environment strategy (`dev` / `stage` / `prod`)** | **Accepted** | Environments | PS6.1 |
| [0006](0006-kubernetes-packaging-helm.md) | **Kubernetes packaging (Helm)** | **Accepted** | K8s packaging | PS6.2 |
| [0007](0007-secrets-management-k8s.md) | **Kubernetes secrets (SOPS / External Secrets)** | **Accepted** | Secrets | PS6.6 |
| [0008](0008-gitops-argocd.md) | **GitOps controller (Argo CD; Flux deferred)** | **Accepted** | GitOps | PS6.7 |
| [0009](0009-gcp-baseline-portable-first.md) | **GCP baseline deploy (portable-first)** | **Accepted** | Cloud / GCP | PS6.8 |

---

## Reading order for reviewers

1. **0002** — current ingest / queue strategy (read first if data path is unclear).
2. **0004** — how LLM backends are selected and rolled out (companion: [llm_gateway.md](../llm_gateway.md)).
3. **0005** — dev / stage / prod matrix and promotion gates.
4. **0006–0009** — deployment path: Helm → secrets → GitOps → GCP.

Superseded **0001** remains for history only.

---

## PS1–PS6 themes without a dedicated ADR

Some PS1–PS4 decisions live in roadmap specs and `docs/` rather than numbered ADRs:

| Theme | Primary doc | Sprint |
|-------|-------------|--------|
| LLM gateway contract | [llm_gateway.md](../llm_gateway.md) | PS1.6 |
| Output schema / fail-closed | [output_schema.md](../output_schema.md) | PS4.2 |
| Prompt injection | [prompt_injection_threat_model.md](../prompt_injection_threat_model.md) | PS4.3 |
| CI gating | [runbooks/ci_gating_policy.md](../runbooks/ci_gating_policy.md) | PS4.7 |
| GPU / NIM backend | [llm_gpu_backend.md](../llm_gpu_backend.md) | PS5.3 |
| Cost guardrails | [llm_cost_guardrails.md](../llm_cost_guardrails.md) | PS5.6 |
| Billing / shutdown | [runbooks/cloud_cost_hygiene.md](../runbooks/cloud_cost_hygiene.md) | PS6.9 |

---

## Adding a new ADR

1. Pick next number (`0010-…`).
2. Append a row to the index table above (do not renumber existing files).
3. Link from [portfolio README](../portfolio/README.md) if cross-cutting.
