# Runbook — GCP stage teardown (trial end / lab shutdown)

Remove SpaceOps **stage** workloads and Terraform-managed resources in `spaceops-project` (or your
`project_id` in `terraform.tfvars`). Stage is **ephemeral by default** per
[stage_operating_policy.md](stage_operating_policy.md); use teardown after PR verification, demos,
or any failed partial recreate that cannot be completed cleanly.

**Automated (recommended):**

```powershell
. .\scripts\refresh_dev_path.ps1
$env:GCP_PROJECT_ID = "spaceops-project"
make gcp-stage-destroy GCP_STAGE_ARGS="--confirm"
```

Non-interactive Terraform (skips `yes` prompt):

```powershell
make gcp-stage-destroy GCP_STAGE_ARGS="--confirm --terraform-auto-approve"
```

By default the automated teardown restores the Terraform-managed billing budget alert after removing
the ephemeral stage resources. To retire the project/account and remove the alert too:

```powershell
make gcp-stage-destroy GCP_STAGE_ARGS="--confirm --terraform-auto-approve --destroy-budget-alert"
```

**Manual order:**

1. `helm uninstall spaceops -n spaceops-stage` (removes PR1.1 Prometheus/Grafana/postgres-exporter
   when the monitoring overlay was enabled)
2. `kubectl delete namespace spaceops-stage` (also removes `spaceops-stage-monitoring-secrets` if
   created for Grafana admin password)
3. Optional: `kubectl delete namespace argocd`
4. `cd infra/terraform/gcp && terraform destroy`
5. Unless retiring the project, restore the alert:
   `terraform apply "-target=google_billing_budget.spaceops"`
6. Verify: `gcloud container clusters list`, `gcloud artifacts repositories list`,
   `gcloud billing budgets list --billing-account=YOUR_BILLING_ACCOUNT`

---

## Terraform state vs live cluster

| Situation | What `terraform destroy` removes |
|-----------|----------------------------------|
| State lists `google_container_cluster.primary` | Cluster + node pool |
| State only has AR/IAM (targeted apply) | **Only** those resources — GKE may remain |
| Empty state, cluster still running | **Nothing** — delete cluster manually |

## Auth failure during destroy

If `terraform destroy` or `terraform plan -destroy` fails with:

```text
oauth2: "invalid_grant" "reauth related error (invalid_rapt)"
```

or `gcloud` says it cannot prompt during non-interactive execution, refresh both user and ADC
credentials before retrying:

```powershell
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project spaceops-project
gcloud config set project spaceops-project

cd infra/terraform/gcp
terraform plan -destroy
terraform destroy
```

If the old trial account cannot be reauthenticated, clean up from the GCP Console:

1. Delete GKE cluster `spaceops-stage` if present.
2. Delete Artifact Registry repository `spaceops` if present.
3. Delete service accounts `spaceops-deploy` and `spaceops-eso-stage` if present.
4. Delete budget alert `spaceops-stage-monthly` if present.
5. Disable billing or delete the old project.

If the cluster predates Terraform state:

```powershell
gcloud container clusters delete spaceops-stage `
  --region us-central1 `
  --project spaceops-project `
  --quiet
```

---

## After teardown

| Item | Action |
|------|--------|
| Old project | Leave empty or delete project in Console (Billing → unlink) |
| New trial account | New project, new `terraform.tfvars`, new `GCP_PROJECT_ID` |
| Repo / Helm / runbooks | Unchanged — reuse for next account |
| PS7.1 live proof | Re-run PS7.1 checklist on **new** project when ready |

## Policy verification

After teardown, verify the selected ephemeral policy:

```powershell
gcloud container clusters list --project $env:GCP_PROJECT_ID --region us-central1
gcloud artifacts repositories list --project $env:GCP_PROJECT_ID --location us-central1
cd infra/terraform/gcp
terraform state list
```

Expected: no `spaceops-stage` cluster, no transient Artifact Registry repository unless intentionally
kept, and Terraform state limited to persistent budget-alert resources unless a long-lived window is
approved. See [stage_operating_policy.md](stage_operating_policy.md) for drift detection and RTO.

## Local cleanup before migrating accounts

Do this only after the old project is destroyed or intentionally abandoned:

```powershell
cd infra/terraform/gcp
terraform state list          # optional audit before deletion

# Local-only files; all are gitignored.
Remove-Item -LiteralPath .\terraform.tfvars -ErrorAction SilentlyContinue
Remove-Item -LiteralPath .\terraform.tfstate -ErrorAction SilentlyContinue
Remove-Item -LiteralPath .\terraform.tfstate.backup -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force -LiteralPath .\.terraform -ErrorAction SilentlyContinue
```

Then create a fresh `terraform.tfvars` for the new account from `terraform.tfvars.example`.

---

## Cross-links

- [gcp_stage_deploy.md](gcp_stage_deploy.md) — bring-up
- [stage_operating_policy.md](stage_operating_policy.md) — stage ownership, cost, RTO, drift checks
- [cloud_cost_hygiene.md](cloud_cost_hygiene.md) — budgets and orphans
- [PS7.1 spec](../../roadmap/02-production-scale/sprint-7/PS7.1-live-stage-gke-deploy.md)
