# SpaceOps — Portfolio overview (PS6.10)

One-page entry for **external reviewers**: what the system is, how to run it locally, how demos work,
and where deeper docs live. Canonical technical detail remains in [docs/README.md](../README.md) and
[roadmap/goals.md](../../roadmap/goals.md).

**Task:** [PS6.10](../../roadmap/02-production-scale/sprint-6/PS6.10-portfolio-artifacts-bundle.md)

---

## What it is

SpaceOps Mission Agent Lab is an **agentic anomaly-triage system** for satellite / ground-segment
operations: ingest telemetry → LangGraph agent (triage → investigate → decide → act → report) →
evidence-backed report or **escalation packet** for human review. Tools run behind **MCP servers**;
restricted actions pass through **OPA policy** and optional **human approval**.

| Property | Implementation |
|----------|----------------|
| Agent runtime | LangGraph + FastAPI API |
| Tools | MCP (telemetry, KB, ticket, gitops) |
| Policy | OPA Rego (`infra/opa/`) |
| Evidence store | Postgres + pgvector; NATS ingest (ADR 0002) |
| Observability | OTel → Jaeger; Prometheus/Grafana · prod gaps: [monitoring-production-analysis.md](../monitoring-production-analysis.md) (PS7.4) |
| Packaging | Docker Compose (dev) · Helm / kind (PS6) · GCP skeleton (PS6.8) |

### Architecture diagram

Primary reference: [system_architecture.mmd](../architecture/system_architecture.mmd) (render in GitHub
or Mermaid Live). Pipeline flow:
[workflow/end_to_end_pipeline.mmd](../workflow/end_to_end_pipeline.mmd).

```
[Ingest] → [API] → [Agent/LangGraph] → MCP tools → [Report | Escalation]
                ↓              ↓
            Postgres       OPA / Approval
                ↓
         OTel / Jaeger / Audit log
```

**Screenshots / traces (placeholders for live review):**

| Artifact | Local URL (after stack up) |
|----------|----------------------------|
| Jaeger UI | `http://localhost:16686` — search `service.name=spaceops-api` |
| Grafana | `http://localhost:3000` (admin/admin) |
| API health | `http://localhost:8000/health` |
| UI (optional) | `http://localhost:3001` if UI profile enabled |

---

## Run locally (< 30 min)

### Prerequisites

- Docker Desktop, Python 3.12, `pip install -r requirements.txt`
- Copy [`.env.example`](../../.env.example) → `.env`; set `OPENAI_API_KEY` (or another `LLM_BACKEND`)

### Compose path (default demo)

```bash
docker compose -f infra/docker-compose.yml --project-directory . up -d
curl http://localhost:8000/health
curl -X POST "http://localhost:8000/ingest?source=telemetry" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @data/telemetry/telemetry.ndjson
```

Full walkthrough: [demo_15min.md](../runbooks/demo_15min.md).

### Local Kubernetes path (PS6)

```bash
make k8s-up
make k8s-smoke          # port-forward + GET /health
make k8s-status
```

Details: [local_k8s_dev.md](../runbooks/local_k8s_dev.md).

### Cloud path (optional stretch)

Terraform + GKE stage: [gcp_stage_deploy.md](../runbooks/gcp_stage_deploy.md) (requires live GCP).
Teardown: [gcp_stage_teardown.md](../runbooks/gcp_stage_teardown.md) (`make gcp-stage-down`).

---

## Demo scenarios A & B

Both scenarios are runnable on **compose** and documented for **local K8s** (same API contract).

### Scenario A — Report + evidence

**Story:** Clear anomaly with telemetry context → structured report with citations/evidence.

```bash
curl -X POST http://localhost:8000/runs -H "Content-Type: application/json" -d '{
  "incident_id": "portfolio-scenario-a",
  "payload": {
    "time_range_start": "2025-02-14T09:00:00Z",
    "time_range_end": "2025-02-14T11:00:00Z",
    "message": "power bus voltage anomaly",
    "channels": ["bus_voltage"]
  }
}'
```

**Pass criteria:** HTTP 200; response includes report fields (triage, investigation summary); optional
citations when KB/telemetry available; Jaeger trace for the run.

**Eval alignment:** `citation-present` / `triage-power` in [evals/cases.yaml](../../evals/cases.yaml).

**K8s:** `kubectl port-forward svc/spaceops-api -n spaceops-dev 8000:8000` then same `curl`.

### Scenario B — Escalation

**Story:** Insufficient / conflicting evidence → escalation packet (no silent autonomous action).

```bash
curl -X POST http://localhost:8000/runs -H "Content-Type: application/json" -d '{
  "incident_id": "portfolio-scenario-b",
  "payload": {
    "time_range_start": "2025-02-14T09:00:00Z",
    "time_range_end": "2025-02-14T09:00:01Z",
    "ref": "no-data"
  }
}'
```

**Pass criteria:** Escalation indicated (`escalated: true` or `escalation_packet` with reason e.g.
`no_evidence`); restricted steps not executed without OPA + approval.

**Eval alignment:** `must-escalate-no-evidence` in [evals/cases.yaml](../../evals/cases.yaml).

**K8s:** Same port-forward; verify escalation in API response and Jaeger span attributes.

### Trace link

After either scenario, open Jaeger → find trace by `incident_id` tag or latest `POST /runs` span.
Placeholder deep link pattern: `http://localhost:16686/trace/{trace_id}`.

---

## LLM backends (PS5)

| Backend | Use case | Doc |
|---------|----------|-----|
| `openai` | Default demos / CI | [llm_gateway.md](../llm_gateway.md) |
| `gpu` | Optional NIM (compose profile) | [llm_gpu_backend.md](../llm_gpu_backend.md) |
| Cost caps | Token budget per run/day | [llm_cost_guardrails.md](../llm_cost_guardrails.md) |
| Parity | OpenAI vs GPU promotion | [evals_backend_parity.md](../evals_backend_parity.md) |

Rollout and fallback: [llm_backend_rollout.md](../runbooks/llm_backend_rollout.md),
[llm_backend_fallback.md](../runbooks/llm_backend_fallback.md).

---

## ADR index

Cross-cutting decisions: [docs/adr/README.md](../adr/README.md) (0001–0010, append-only log).

| Theme | ADR | Sprint |
|-------|-----|--------|
| Queue / ingest | [0002](../adr/0002-ingest-nats-first-postgres-evidence-store.md) (0001 superseded) | PS3 |
| Checkpoint | [0003](../adr/0003-langgraph-durable-checkpoint-postgres.md) | PS3 |
| LLM gateway / backends | [0004](../adr/0004-llm-backend-rollout.md) | PS5 |
| Environments | [0005](../adr/0005-environment-strategy-dev-stage-prod.md) | PS6.1 |
| Helm / K8s packaging | [0006](../adr/0006-kubernetes-packaging-helm.md) | PS6.2 |
| Secrets | [0007](../adr/0007-secrets-management-k8s.md) | PS6.6 |
| GitOps | [0008](../adr/0008-gitops-argocd.md) | PS6.7 |
| GCP baseline | [0009](../adr/0009-gcp-baseline-portable-first.md) | PS6.8 |
| Multi-cloud burst | [0010](../adr/0010-multicloud-burst-routing.md) | PS7.7 |

Gateway contract detail (non-ADR): [llm_gateway.md](../llm_gateway.md).

---

## Threat model (summary)

Full page: [threat_model.md](../threat_model.md). Maps prompt injection, tool abuse, data poisoning,
and secrets leakage to PS4/PS5/PS6 controls (tests, OPA, evals, runbooks).

---

## Runbook pack index

| Runbook | Audience | When to use |
|---------|----------|-------------|
| [demo_15min.md](../runbooks/demo_15min.md) | Dev / reviewer | First live demo on compose |
| [local_k8s_dev.md](../runbooks/local_k8s_dev.md) | Dev | kind + Helm local cluster |
| [k8s_rollout_rollback.md](../runbooks/k8s_rollout_rollback.md) | Dev / SRE | Helm upgrade / rollback |
| [graph_worker_checkpoint_ops.md](../runbooks/graph_worker_checkpoint_ops.md) | Dev / SRE | Checkpoint resume after pod kill / rollout (PS6.11) |
| [k8s_environment_isolation.md](../runbooks/k8s_environment_isolation.md) | SRE | NetworkPolicy, RBAC, quotas |
| [k8s_secrets_bootstrap.md](../runbooks/k8s_secrets_bootstrap.md) | Dev / SRE | K8s Secrets / ESO bootstrap |
| [gitops_bootstrap.md](../runbooks/gitops_bootstrap.md) | Dev / SRE | Optional Argo CD (PS6.7) |
| [gitops_agent_pr_demo.md](../runbooks/gitops_agent_pr_demo.md) | Dev / SRE | Agent `create_pr` → Argo deploys ops-config |
| [gitops_pr_demo.md](../runbooks/gitops_pr_demo.md) | Dev / SRE | Argo CD promotion via Git PR |
| [environment_promotion.md](../runbooks/environment_promotion.md) | Dev / SRE | dev → stage → prod gates |
| [gcp_stage_deploy.md](../runbooks/gcp_stage_deploy.md) | SRE | GKE stage deploy (stretch) |
| [gcp_stage_teardown.md](../runbooks/gcp_stage_teardown.md) | SRE | GKE stage teardown (`make gcp-stage-down`) |
| [cloud_cost_hygiene.md](../runbooks/cloud_cost_hygiene.md) | SRE / FinOps | GCP budget, scale-down |
| [gpu_cost_hygiene.md](../runbooks/gpu_cost_hygiene.md) | Dev | Local NIM idle TTL (PS5.7) |
| [llm_cost_guardrails.md](../runbooks/llm_cost_guardrails.md) | Dev / SRE | Token budget incidents |
| [llm_backend_rollout.md](../runbooks/llm_backend_rollout.md) | Dev / SRE | Backend migration |
| [llm_backend_fallback.md](../runbooks/llm_backend_fallback.md) | SRE | GPU → OpenAI fallback |
| [multicloud_burst_routing.md](../runbooks/multicloud_burst_routing.md) | SRE / Platform | PS7.7 burst routing simulation and kill-switch audit |
| [ci_gating_policy.md](../runbooks/ci_gating_policy.md) | Dev | Hard vs soft CI gates (PS4.7) |
| [guardrails_minimum_hardening.md](../runbooks/guardrails_minimum_hardening.md) | Dev | Fail-closed escalation rules |
| [guardrails_quality_triage.md](../runbooks/guardrails_quality_triage.md) | Dev | CI gate failure triage |
| [distributed_tracing_ps19.md](../runbooks/distributed_tracing_ps19.md) | Dev / SRE | Trace propagation |
| [replay_workflow.md](../runbooks/replay_workflow.md) | Dev | Deterministic replay |
| [post_incident_loop.md](../runbooks/post_incident_loop.md) | Ops | Post-incident learning |
| [db_migrations.md](../runbooks/db_migrations.md) | Dev | Postgres migrations |
| [queue_dlq_recovery.md](../runbooks/queue_dlq_recovery.md) | SRE | NATS / DLQ recovery |
| [add_new_mcp.md](../runbooks/add_new_mcp.md) | Dev | Extend tool surface |
| [add_eval_case.md](../runbooks/add_eval_case.md) | Dev | Add eval coverage |
| [fixture_upload_simulation.md](../runbooks/fixture_upload_simulation.md) | Dev | Fixture / simulate flows |

---

## Dependency hygiene

| Control | Location |
|---------|----------|
| Pinned Python deps | [requirements.txt](../../requirements.txt) (exact pins for CI reproducibility) |
| Dependabot | [.github/dependabot.yml](../../.github/dependabot.yml) — weekly pip + GitHub Actions |
| Local audit | `pip audit` (run manually; not a hard CI gate) |
| Pre-commit | ruff, ruff-format, mypy, pytest subset — see root [README](../../README.md) |
| Safety CI | `.github/workflows/ci.yml` — OPA, injection, guardrails, golden baselines (PS4.7) |

SBOM generation is **out of scope** for PS6.10; Dependabot + pinned requirements satisfy minimum
portfolio hygiene per [roadmap § Cross-Cutting Artifacts](../../roadmap/02-production-scale.md#cross-cutting-engineering-artifacts-portfolio-grade).

---

## External reviewer checklist

Use this list for a < 30 min review session (compose path):

- [ ] Read this page + [threat_model.md](../threat_model.md) (5 min)
- [ ] Copy `.env.example` → `.env`; set `OPENAI_API_KEY`
- [ ] `docker compose -f infra/docker-compose.yml --project-directory . up -d`
- [ ] `curl http://localhost:8000/health` → OK
- [ ] Ingest fixture (`telemetry.ndjson`) per Scenario A prep above
- [ ] Run **Scenario A** `POST /runs` → report with evidence fields
- [ ] Run **Scenario B** `POST /runs` → escalation packet / `escalated`
- [ ] Open Jaeger (`localhost:16686`) → locate one run trace
- [ ] Skim [ADR index](../adr/README.md) and one runbook from the table above
- [ ] Optional: `python -m evals.scoring` (requires LLM key; proves injection MoE3 = 0 target)
- [ ] Optional K8s: `make k8s-up && make k8s-smoke`

**Role-play acceptance:** reviewer can explain **infra $ vs model $** using
[cloud_cost_hygiene.md](../runbooks/cloud_cost_hygiene.md) vs
[llm_cost_guardrails.md](../runbooks/llm_cost_guardrails.md).

---

## Related

- [Root README](../../README.md) — developer quick start
- [docs/README.md](../README.md) — diagram index
- [roadmap/02-production-scale.md](../../roadmap/02-production-scale.md) — PS phase goals
