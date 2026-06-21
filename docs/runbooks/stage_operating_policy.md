# Stage operating policy (PR1.3)

This runbook is the canonical operating policy for the SpaceOps `stage` environment during
Production Readiness. It turns the PS6/PS7 GKE stage lab into a repeatable production-pilot
environment without keeping an expensive always-on cluster by accident.

## Policy decision

**Selected policy:** ephemeral stage by default, with a tested recreate path and persistent budget
alert.

Rationale:

- Current GKE stage is a lab/pilot environment, not customer production.
- `make gcp-stage-up` and `make gcp-stage-down` already encode the full bring-up and teardown path.
- Terraform restores the persistent billing budget alert after ephemeral resources are destroyed.
- A long-lived cluster is allowed only for scheduled soak, demo, or incident-drill windows with an
  explicit owner and end time.

## Operating modes

| Mode | When | Owner | Required controls |
|------|------|-------|-------------------|
| Ephemeral stage | Default PR work, demos, PR1.4 test packs | Platform owner | Budget alert enabled, recreate drill evidence, teardown same day |
| Time-boxed long-lived stage | Soak, game day, external review window | Platform owner + mission-agent owner | End date, cost cap, daily drift check, scheduled scale-down |
| Production pilot candidate | After PR1-PR3 review | Production readiness owner | Go/no-go review, backup/restore drill, security sign-off |

## Ownership

| Responsibility | Primary owner | Backup |
|----------------|---------------|--------|
| Terraform/GKE/Artifact Registry | Platform owner | Production readiness owner |
| Helm release and values overlays | Platform owner | Mission-agent owner |
| App smoke/demo scenarios | Mission-agent owner | Platform owner |
| Secrets bootstrap and rotation | Platform owner | Security reviewer |
| Cost/budget guardrails | Platform owner | Project owner |
| Production-readiness evidence | Production readiness owner | Sprint owner |

## Budget and cost guardrails

- Budget alert must stay enabled for the project unless the project is being retired.
- Default budget threshold source: [cloud_cost_hygiene.md](cloud_cost_hygiene.md).
- Ephemeral stage should be torn down after demos, PR verification, or the same working day.
- Long-lived stage must have a recorded end date and either node scale-down or full teardown plan.
- `--destroy-budget-alert` is only allowed when retiring the GCP project/account.
- Monthly orphan review must include GKE clusters, Artifact Registry repositories, disks, load
  balancers, Secret Manager versions, and unused IP addresses.

## Secret bootstrap policy

Stage must use the stage/prod path from [k8s_secrets_bootstrap.md](k8s_secrets_bootstrap.md):

1. Secrets live in Google Secret Manager or another approved external backend.
2. External Secrets Operator syncs them into `spaceops-stage`.
3. Helm uses `secrets.create=false` and `secrets.existingSecret=spaceops-stage-secrets`.
4. Local imperative `k8s-secrets-bootstrap` is allowed only for throwaway local clusters, not shared
   stage.

Verification for each recreate:

```bash
kubectl get externalsecret,secret -n spaceops-stage
kubectl describe externalsecret -n spaceops-stage
```

The PR1.3 repo baseline verifies the documented bootstrap path. Live secret sync evidence belongs
to the first stage recreate or PR1.4 test window.

## Helm and GitOps ownership

Pick exactly one owner for the `spaceops` release in `spaceops-stage`.

| Owner | Use when | Drift command | Remediation |
|-------|----------|---------------|-------------|
| Imperative Helm | Lab, first deploy, debugging, PR1.1-PR1.4 drills | `helm status spaceops -n spaceops-stage` and `helm get values spaceops -n spaceops-stage` | Re-run `make gcp-stage-deploy` with the expected overlays |
| Argo CD GitOps | Ongoing stage sync from Git | `make gitops-status` and Argo app health/sync status | Commit values change or sync/rollback through Argo |

Do not let Argo CD and imperative Helm mutate the same release at the same time. If migrating from
imperative Helm to GitOps, uninstall the Helm release or use a deliberate adoption procedure before
enabling Argo ownership.

## Drift detection drill

Run before demos, during long-lived windows, and after manual debugging:

```bash
$env:GCP_PROJECT_ID = "spaceops-project-498213"
gcloud container clusters list --project $env:GCP_PROJECT_ID --region us-central1
kubectl config current-context
kubectl get pods,deploy,svc -n spaceops-stage -o wide
helm status spaceops -n spaceops-stage
helm get values spaceops -n spaceops-stage
cd infra/terraform/gcp
terraform plan
```

Expected result:

- Terraform plan has no unexpected create/replace/destroy actions.
- Helm release owner matches the selected ownership mode.
- Monitoring overlay is present when PR1.1/PR1.2 evidence is required.
- No stale kubeconfig points to a deleted `spaceops-stage` cluster.

If the cluster is intentionally absent, drift check passes only when Terraform state does not contain
stage resources beyond the persistent budget-alert resources and `gcloud container clusters list`
shows no `spaceops-stage` cluster.

## Recreate RTO

| Path | Target RTO | Notes |
|------|------------|-------|
| Infra only (`terraform apply`) | <= 30 min | Depends on GKE regional capacity and API enablement |
| Images (`make gcp-stage-images`) | <= 20 min | Requires Docker Desktop/daemon and Artifact Registry |
| Helm deploy + migrations | <= 15 min | Includes API, MCP, Postgres, NATS, OTel/Jaeger |
| Smoke + scenario A/B | <= 10 min | `make gcp-stage-smoke` and `make gcp-stage-demo` |
| Full recreate target | <= 75 min | Excludes manual creation of new real secrets |

Current known blocker: image build/push requires a running Docker daemon. If Docker is unavailable,
stop after teardown and record the failed recreate attempt instead of leaving partial cloud
resources running.

## Demo readiness checklist

Before an external demo or production-readiness evidence window:

- [ ] `GCP_PROJECT_ID`, region, and billing account are confirmed.
- [ ] Budget alert exists and notification email is correct.
- [ ] Stage owner and teardown time are recorded.
- [ ] Secrets sync is healthy in `spaceops-stage`.
- [ ] `make gcp-stage-smoke` passes.
- [ ] Scenario A/B demo passes or has a documented known limitation.
- [ ] PR1.1 monitoring targets are UP when monitoring evidence is required.
- [ ] PR1.2 alert rules are loaded when SLO evidence is required.
- [ ] Drift check has no unexpected Terraform or Helm changes.
- [ ] Teardown command and owner are known before the demo starts.

## Teardown rules

- Default: run `make gcp-stage-down` after PR verification or demo completion.
- Use `make gcp-stage-destroy GCP_STAGE_ARGS="--confirm --terraform-auto-approve"` for
  non-interactive cleanup.
- Keep the budget alert unless retiring the project.
- Verify no GKE cluster, Artifact Registry repository, or orphan compute resources remain.
- If teardown fails due to auth, use the manual recovery in [gcp_stage_teardown.md](gcp_stage_teardown.md).

## PR1.3 evidence

This task records the policy and static drill path. Live stage recreate evidence is expected during
the next stage bring-up or PR1.4 soak/failure pack.

Static evidence:

- Deploy and teardown runbooks link to this policy.
- Cost guardrails, secret bootstrap, ownership, drift detection, and RTO are documented.
- Tests assert the policy, cross-links, and PR1.3 board/spec status.

## Cross-links

- [gcp_stage_deploy.md](gcp_stage_deploy.md)
- [gcp_stage_teardown.md](gcp_stage_teardown.md)
- [cloud_cost_hygiene.md](cloud_cost_hygiene.md)
- [k8s_secrets_bootstrap.md](k8s_secrets_bootstrap.md)
- [gitops_bootstrap.md](gitops_bootstrap.md)
- [slo-production-readiness.md](../slo-production-readiness.md)
