# Stage soak, load, and failure test pack (PR1.4)

This runbook defines the Production Readiness PR1.4 evidence pack for stage reliability. It is the
bridge between demo smoke checks and a production-pilot readiness review.

## Scope

PR1.4 validates that the stage stack can run longer than a demo and recover from expected failures.
It uses the PR1.1 monitoring overlay and PR1.2 SLO rules.

Required stack:

- GKE stage following [stage_operating_policy.md](stage_operating_policy.md).
- Helm deploy with `values-stage-full.yaml` and `values-monitoring-stage.yaml`.
- Prometheus targets UP for API, NATS, OTel Collector, and postgres-exporter.
- Scenario A/B demo path from [gcp_stage_deploy.md](gcp_stage_deploy.md).

## Profiles

| Profile | Duration | Fixture mix | Goal |
|---------|----------|-------------|------|
| `dry-run` | immediate | no live calls | Validate plan, thresholds, failure matrix, and report schema in CI. |
| `pilot-short` | 30 min | 70% Scenario A, 20% Scenario B, 10% ingest-only | First live stage confidence run after recreate. |
| `pilot-full` | 2 h | Same mix, repeated every 2 min | Production-readiness evidence before PR1 closure. |

## Load limits

These are intentionally conservative for the current single-node/preemptible stage profile.

| Surface | Pilot-short limit | Pilot-full limit | Acceptance |
|---------|-------------------|------------------|------------|
| API `/health` | 1 request / 10s | 1 request / 10s | 100% success during run |
| API `/runs` | 3 concurrent runs | 5 concurrent runs | p95 <= 60s, error rate <= 5% |
| Ingest / NATS | 100 telemetry lines / min | 250 telemetry lines / min | No sustained NATS scrape loss |
| Agent worker | 1 replica if Variant A enabled | 1-2 replicas if explicitly enabled | Queue drains after restart; no stuck leased jobs |
| Postgres | stage PVC / single StatefulSet | stage PVC / single StatefulSet | exporter UP; no migration/schema errors |

Do not exceed these limits on the lab GKE profile without resizing nodes and updating this runbook.

## Failure scenarios

| ID | Scenario | Command / trigger | Expected behavior | Owner |
|----|----------|-------------------|-------------------|-------|
| F1 | API pod restart | `kubectl rollout restart deploy/spaceops-api -n spaceops-stage` | New pod Ready; `/health` recovers; no data loss. | Platform |
| F2 | Agent worker restart | `kubectl delete pod -n spaceops-stage -l app.kubernetes.io/component=agent-worker --wait=false` | Variant A lease is reclaimed; Variant B records N/A. | Mission-agent |
| F3 | OPA unavailable | `kubectl scale deploy/spaceops-opa -n spaceops-stage --replicas=0` | Restricted action fails closed; OPA failure alert or metric increments. | Security |
| F4 | Postgres restart | `kubectl rollout restart statefulset/spaceops-postgres -n spaceops-stage` | API reports temporary failure then recovers; no schema loss. | Data |
| F5 | Queue/DLQ pressure | Repeated ingest fixture bursts, then inspect DLQ endpoint/table | No unbounded DLQ growth; recovery path documented. | Platform |
| F6 | LLM backend failure | Point backend to invalid endpoint or use no-key test window | Run escalates with provider/tool failure, no unsafe action. | Mission-agent |
| F7 | Budget exhaustion | Set temporary low `LLM_DAILY_TOKEN_BUDGET` in a throwaway overlay | Run escalates with `budget_exceeded`; no backend fallback on budget deny. | Cost |

Always restore state after F3/F6/F7 before continuing:

```bash
kubectl scale deploy/spaceops-opa -n spaceops-stage --replicas=1
kubectl rollout status deploy/spaceops-opa -n spaceops-stage --timeout=3m
make gcp-stage-deploy GCP_STAGE_DEPLOY_ARGS="--monitoring"
```

## Acceptance thresholds

The run passes only when all required checks are true:

- API availability during test window: 100% for `pilot-short`, >= 99% for `pilot-full`.
- API run p95 latency: <= 60 seconds.
- Run error rate: <= 5% excluding the intentional failure window.
- Scenario A returns report + evidence after recovery.
- Scenario B escalates.
- OPA unavailable and LLM/budget failures fail closed.
- Prometheus targets recover to UP after each failure scenario.
- No page-severity PR1.2 alert remains firing at the end of the run.
- Any failed acceptance item is converted to a backlog/task with owner.

## Automation

CI-safe dry-run:

```powershell
make pr14-stage-test-pack
```

Write a report artifact:

```powershell
make pr14-stage-test-pack PR14_ARGS="--profile dry-run --write-report var/pr14/latest.json"
```

Live stage plan preview:

```powershell
make pr14-stage-test-pack PR14_ARGS="--profile pilot-short --mode plan"
```

Live execution is intentionally explicit and should be run only inside a time-boxed stage window:

```powershell
$env:GCP_PROJECT_ID = "spaceops-project-498213"
make gcp-stage-up GCP_STAGE_DEPLOY_ARGS="--monitoring"
make pr14-stage-test-pack PR14_ARGS="--profile pilot-short --mode live --api-url http://<LB_IP>:8000"
make gcp-stage-down
```

Current `--mode live` scope is limited: it runs stage smoke + Scenario A/B and writes the same report
schema with the failure matrix still marked for operator execution. It does **not** automate the
30-minute or 2-hour soak loop, concurrent load, F1-F7 disruptive actions, Prometheus observations,
or backlog creation. Use the matrix and thresholds in this runbook as the source of truth for the
full live drill.

## Report requirements

Each run report must include:

- profile, start/end time, operator, project, namespace
- command plan and whether it was dry-run or live
- soak/load thresholds
- failure scenario results and restoration notes
- Prometheus/SLO observations where available
- backlog items for every failed or skipped required scenario

Use JSON reports for automation and summarize the final result in the PR1 sprint review.

## Current evidence

PR1.4 repository evidence includes a dry-run report generated by `scripts/stage_pr14.py` and one
failed live attempt on 2026-06-22. The live attempt proved the current preemptible single-node GKE
profile is not stable enough for PR1.4: Scenario A timed out, the node was replaced during the run,
and Postgres became Pending because of PersistentVolume node-affinity scheduling. Full passing live
stage evidence is still required before PR1 closure or production-pilot go/no-go.

Before the next live attempt, use the stable Terraform profile:

```bash
cd infra/terraform/gcp
terraform apply -var-file=terraform.pr14-stable.tfvars.example -auto-approve
```

That profile uses non-preemptible nodes and extra capacity for the full monitoring overlay plus
Postgres without rollout surge CPU pressure.

## Cross-links

- [stage_operating_policy.md](stage_operating_policy.md)
- [gcp_stage_deploy.md](gcp_stage_deploy.md)
- [gcp_stage_teardown.md](gcp_stage_teardown.md)
- [slo-production-readiness.md](../slo-production-readiness.md)
- [queue_dlq_recovery.md](queue_dlq_recovery.md)
- [llm_cost_guardrails.md](llm_cost_guardrails.md)
- [graph_worker_checkpoint_ops.md](graph_worker_checkpoint_ops.md)
