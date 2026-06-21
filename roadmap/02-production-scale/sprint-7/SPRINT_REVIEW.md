# PS7 — Sprint review

**Sprint:** Production Scale — Sprint 7 (PS7.1–PS7.8)  
**Board:** [BOARD.md](BOARD.md) — **8 / 8 Done**  
**Date:** 2026-06-03 (initial review); updated 2026-06-20 after PS7.2 drill + PS7b verification

---

## Executive summary

PS7 closed the **PS6 stretch** and **backlog operational debt** before Next-Gen Autonomy (NG1).
Hard scope delivered **live GKE stage proof** (`make gcp-stage-up` / `gcp-stage-down`), **wired GCP
budget alerts** with a dated scale-down drill, **production monitoring analysis** (BL-001), and
**folder README coverage** (BL-002).

PS7b scope also shipped in full: **Variant A graph worker** (queue + agentWorker), **Postgres LLM
budget mode** for stage/prod Helm, **multi-cloud burst ADR + simulation** (BL-004), and **platform
ops triage CLI** (BL-005).

Sprint goal from [README.md](README.md) is **met** at hard scope **and** expanded PS7b bar. The
test suite now collects **416 tests**; representative PS7 modules and portfolio/runbook gates are
listed below. PS7.5 runtime README gitignore handling was fixed so fresh clones keep the required
folder docs.

---

## Goals vs outcomes

| README outcome | Status |
|----------------|--------|
| Stage GKE deploy reproducible; demo A/B in cloud | Done (PS7.1); `spaceops-project-498213`, [gcp_stage_deploy.md](../../../docs/runbooks/gcp_stage_deploy.md), [gcp_stage_teardown.md](../../../docs/runbooks/gcp_stage_teardown.md) |
| GCP budget/alerts verified + runbook drill | Done (PS7.2); budget `spaceops-stage-monthly`, drill 2026-06-14, [cloud_cost_hygiene.md](../../../docs/runbooks/cloud_cost_hygiene.md) §3b |
| Production monitoring analysis (BL-001) | Done (PS7.4); [monitoring-production-analysis.md](../../../docs/monitoring-production-analysis.md) |
| README per folder (BL-002) | Done (PS7.5); `tests/test_readme_per_folder_ps75.py` |
| Optional: Variant A worker | Done (PS7.3); `values-checkpoint-variant-a.yaml`, `tests/test_agent_worker_ps73.py` |
| Optional: postgres LLM budget | Done (PS7.6); `llm_usage_ledger`, stage/prod Helm `budgetMode: postgres` |
| Optional: multi-cloud burst ADR | Done (PS7.7); [ADR 0010](../../../docs/adr/0010-multicloud-burst-routing.md), simulation script |
| Optional: platform ops triage | Done (PS7.8); `scripts/platform_ops_triage.py`, runbook §9 |

---

## Board summary

| Task | Status |
|------|--------|
| PS7.1 Live stage GKE deploy | Done |
| PS7.2 Live billing alerts + cost drill | Done |
| PS7.3 Graph worker Variant A | Done |
| PS7.4 Production monitoring analysis (BL-001) | Done |
| PS7.5 README per folder (BL-002) | Done |
| PS7.6 Postgres LLM budget mode | Done |
| PS7.7 Multi-cloud burst ADR (BL-004) | Done |
| PS7.8 Platform ops triage MVP (BL-005) | Done |

---

## Definition of Done (sprint checklist)

**Hard gates**

1. **Live stage GKE** — `make gcp-stage-up` / `make gcp-stage-down`; demo A/B on `spaceops-project-498213`; `tests/test_gcp_stage.py`.
2. **Live budget + drill** — Terraform budget alert, scale-down drill logged; `tests/test_cloud_cost_ps69.py` (PS7.2 extensions).
3. **Monitoring analysis** — Per-component OK/gap/recommendation; link integrity; `tests/test_monitoring_production_analysis_ps74.py`.
4. **Folder READMEs** — BL-002 folder list + link resolve test; runtime dirs tracked via `.gitignore` negation; `tests/test_readme_per_folder_ps75.py`.

**PS7b (also completed)**

5. **Variant A worker** — Postgres `agent_run_queue`, agentWorker Deployment, checkpoint resume; `tests/test_agent_worker_ps73.py`, checkpoint integration tests.
6. **Postgres LLM budget** — Alembic `llm_usage_ledger`, stage/prod Helm env; `tests/test_llm_cost_postgres_ps76.py`.
7. **Burst routing** — ADR 0010, deterministic simulation, `backend_routing_reason` audit; `tests/test_multicloud_burst_ps77.py`.
8. **Platform ops triage** — Read-only collector + hypotheses; `--apply` gated; `tests/test_platform_ops_ps78.py`.

---

## What shipped (by theme)

### Cloud proof (PS7.1–PS7.2)

- **One-command lifecycle:** `make gcp-stage-up` / `make gcp-stage-down` with budget-preserving teardown (targeted budget restore after destroy).
- **Live deploy evidence:** Terraform + AR + Helm on GKE; portfolio scenarios A/B via `scripts/gcp_stage.py demo`.
- **Cost hygiene:** Budget `spaceops-stage-monthly` (PLN), email notification, scale-down drill (`make cloud-scale-down-check`), teardown runbook §3b dated entry.

### Documentation & backlog (PS7.4–PS7.5)

- **BL-001:** [monitoring-production-analysis.md](../../../docs/monitoring-production-analysis.md) — Compose vs Helm gaps (Prometheus/Grafana on K8s, OTLP TLS, Jaeger retention); PS7b follow-ups listed.
- **BL-002:** READMEs under `data/`, `kb/`, `evals/`, `infra/` (+ runtime folder READMEs with gitignore exceptions).

### Platform depth (PS7.3, PS7.6–PS7.8)

- **PS7.3** — Variant A: `apps/agent/run_queue.py`, `apps/workers/agent_graph.py`, Helm overlay; complements PS6.11 Variant B on api.
- **PS7.6** — Shared UTC-day token cap in Postgres; ADR 0005 §5 updated; stage `250k` / prod `500k` token defaults in Helm.
- **PS7.7** — [0010-multicloud-burst-routing.md](../../../docs/adr/0010-multicloud-burst-routing.md); `apps/llm_burst_routing.py`; kill-switch + audit field on gateway.
- **PS7.8** — `apps/platform_ops/` read-only triage; queue/DLQ runbook §9; separate from mission agent domain.

---

## CI and test footprint

New or extended test modules (representative):

| Area | Tests |
|------|--------|
| GKE stage automation | `test_gcp_stage.py` |
| PS7.2 drill / budget | `test_cloud_cost_ps69.py` |
| Monitoring analysis | `test_monitoring_production_analysis_ps74.py` |
| Folder READMEs | `test_readme_per_folder_ps75.py` |
| Variant A worker | `test_agent_worker_ps73.py` |
| Postgres LLM budget | `test_llm_cost_postgres_ps76.py`, `test_llm_cost_guardrails_ps56.py` |
| Multi-cloud burst | `test_multicloud_burst_ps77.py` |
| Platform ops triage | `test_platform_ops_ps78.py` |
| Portfolio / checkpoint lint | `test_portfolio_ps610.py`, `test_k8s_checkpoint_resume_integration.py` |

**CI fix during sprint:** `portfolio-docs-lint` — lazy import in `scripts/checkpoint_retention.py` so minimal-deps job does not require `psycopg2` for argparse-only test.

**CI fix after initial review:** Runtime data READMEs (`data/incidents/`, etc.) — `.gitignore` changed from directory ignore to `/*` + `!README.md` so PS7.5 files ship on fresh clone.

---

## Operational lessons

| Topic | Lesson |
|-------|--------|
| **GKE lab quotas** | Pin `node_locations` and disk size in Terraform; regional defaults can exhaust SSD quota on small projects. |
| **Artifact Registry order** | Run `make gcp-stage-images` only after Terraform creates the AR repo. |
| **Teardown vs budget** | Default `gcp-stage-down` preserves billing budget alert; use `--destroy-budget-alert` only for project retirement. |
| **Monitoring on GKE stage** | Jaeger/OTel yes; Prometheus/Grafana still Compose-only — documented in PS7.4, not a regression. |
| **Variant A vs B** | Variant B (api checkpoint) remains stage default; Variant A is optional overlay for worker isolation proof. |
| **Postgres budget semantics** | Pre-call enforce blocks the *next* call after cap; concurrent replicas may overshoot slightly — document in runbooks. |
| **Gitignored READMEs** | Folder READMEs inside runtime dirs must use gitignore negation or they never reach CI. |
| **Platform vs mission agent** | BL-005 triage is SRE/transport domain; do not conflate with LangGraph anomaly pipeline. |

---

## ADR and backlog closure

| Item | Resolution |
|------|------------|
| **BL-001** | Done → PS7.4 analysis doc |
| **BL-002** | Done → PS7.5 READMEs + test |
| **BL-004** | Done → ADR 0010 + simulation (live cloud B deferred) |
| **BL-005** | Done → PS7.8 read-only MVP |
| **ADR 0005 §5** | Updated — stage/prod use `LLM_BUDGET_MODE=postgres` when cap > 0 |
| **ADR 0010** | New — multi-cloud burst policy (simulation + audit) |
| **ADR 0011** | Reserved for NG1 supervisor graph (not PS7) |

---

## Risks and carryover

| Risk | Mitigation |
|------|------------|
| **Stage cluster not permanent** | Treat GKE as lab; re-run `gcp-stage-up` before external demos; document cost in PS7.2 runbook. |
| **Prometheus/Grafana gap on K8s** | PS7.4 PS7b-M1 follow-up; do not claim full prod observability until wired. |
| **Live multi-cloud burst** | ADR 0010 Stage 2+; simulation and audit only in PS7.7. |
| **Platform ops `--apply`** | MVP read-only; replay remediate stays manual via `scripts/replay_queue.py`. |
| **Checkpoint + worker ops** | Run Variant A overlay only when queue/worker proof needed; operator runbook for kill/resume. |

---

## Recommendation

**Close PS7** for planning and delivery. Hard scope (live cloud + backlog docs) and PS7b expansions
are integrated, tested, and documented.

**Next:** [NG sprint 1](../../03-next-gen-autonomy/sprint-1/) — multi-agent supervisor (ADR 0011);
stage/cloud optional for NG local proof. Optional follow-ups from PS7.4 (Helm Prometheus, OTLP TLS,
managed Jaeger) remain PS7b-M* items, not NG blockers.

---

## Actions captured in repo

- [README.md](README.md) — Definition of Done: all hard + PS7b checkboxes complete.
- [BOARD.md](BOARD.md) — 8/8 Done; sprint closed reference.
- [SPRINT_REVIEW.md](SPRINT_REVIEW.md) — this file.
- [../README.md](../README.md) — PS7 row references live cloud + backlog closure.
