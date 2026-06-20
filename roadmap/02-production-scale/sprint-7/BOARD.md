# PS7 — Board

| Task | Title | Status | Spec |
|------|-------|--------|------|
| PS7.1 | Live stage GKE deploy (PS6.8 stretch) | Done | [PS7.1](PS7.1-live-stage-gke-deploy.md) — stage GKE deploy + smoke + demo A/B passed on `spaceops-project-498213` |
| PS7.2 | Live GCP billing alerts + cost drill (PS6.9 stretch) | Done | [PS7.2](PS7.2-live-billing-alerts-drill.md) — budget `spaceops-stage-monthly` + scale-down drill 2026-06-14 |
| PS7.4 | Production monitoring stack analysis (BL-001) | Done | [PS7.4](PS7.4-monitoring-production-analysis.md) — [monitoring-production-analysis.md](../../../docs/monitoring-production-analysis.md) |
| PS7.5 | README per folder coverage (BL-002) | Done | [PS7.5](PS7.5-readme-per-folder.md) — data/kb/evals/infra subfolders + tests |
| PS7.3 | Graph worker Variant A (PS6.11 defer) | Done | [PS7.3](PS7.3-graph-worker-variant-a.md) — agentWorker + Postgres queue + checkpoint resume |
| PS7.6 | Postgres LLM budget mode (PS7b) | Deferred | [PS7.6](PS7.6-postgres-llm-budget-mode.md) |
| PS7.7 | Multi-cloud burst ADR (BL-004, PS7b) | Deferred | [PS7.7](PS7.7-multicloud-burst-adr.md) |
| PS7.8 | Platform ops triage agent MVP (BL-005, PS7b) | Deferred | [PS7.8](PS7.8-platform-ops-triage-agent.md) |

**Status key:** Todo | In progress | Done | Blocked | Deferred

**Hard scope (PS7 close):** PS7.1, PS7.2, PS7.4, PS7.5 — see [README.md](README.md).

**Plan notes**

- **PS7.2** requires GCP credentials — PS7.4–PS7.5 can run in parallel without cloud.
- **PS7.3** does not block NG1; Variant B is enough to start multi-agent locally.
- **PS7.3, PS7.6–PS7.8** default to **PS7b** unless hard scope finishes early.
