# Runbook — GCP stage teardown (trial end / lab shutdown)

Remove SpaceOps **stage** workloads and Terraform-managed resources in `spaceops-project` (or your
`project_id` in `terraform.tfvars`). Use when the free trial ends or you move to a **new GCP account**.

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

**Manual order:**

1. `helm uninstall spaceops -n spaceops-stage`
2. `kubectl delete namespace spaceops-stage`
3. Optional: `kubectl delete namespace argocd`
4. `cd infra/terraform/gcp && terraform destroy`
5. Verify: `gcloud container clusters list`, `gcloud artifacts repositories list`

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
- [cloud_cost_hygiene.md](cloud_cost_hygiene.md) — budgets and orphans
- [PS7.1 spec](../../roadmap/02-production-scale/sprint-7/PS7.1-live-stage-gke-deploy.md)
