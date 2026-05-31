# GCP Terraform — SpaceOps stage baseline (PS6.8)

Minimal **portable-first** IaC for a small GKE stage cluster and Artifact Registry. Not a full
landing zone. Application manifests remain Helm/Kubernetes — no GKE-specific code in `apps/`.

See [ADR 0009](../../../docs/adr/0009-gcp-baseline-portable-first.md) and
[runbook: GCP stage deploy](../../../docs/runbooks/gcp_stage_deploy.md).

## What this creates

| Resource | Purpose |
|----------|---------|
| GKE cluster | Small regional cluster (`e2-standard-2`, 1 node default) |
| Artifact Registry | Docker repo `spaceops` for `api`, `mcp`, … |
| `spaceops-deploy` SA | CI push + Helm deploy (`artifactregistry.writer`, `container.developer`) |
| `spaceops-eso-stage` SA | ESO → Google Secret Manager via Workload Identity (PS6.6) |
| Labels | `env`, `app`, `managed-by` for cost allocation ([PS6.9](../../../roadmap/02-production-scale/sprint-6/PS6.9-billing-shutdown-controls.md)) |

**Out of scope:** multi-region HA, GPU node pools (Phase 7), Cloud Run (documented as fallback only).

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.5
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) authenticated
- GCP project with billing enabled
- Roles: `roles/owner` or equivalent for first apply (API enablement, GKE, IAM)

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `project_id` | *(required)* | GCP project ID |
| `region` | `us-central1` | Region for GKE + AR |
| `environment` | `stage` | Label `env=` (`dev` \| `stage` \| `prod`) |
| `cluster_name` | `spaceops-stage` | GKE cluster name |
| `node_locations` | `["us-central1-a"]` | Single-zone lab node placement inside regional control plane |
| `node_count` | `1` | Node pool size |
| `machine_type` | `e2-standard-2` | GCE type |
| `preemptible_nodes` | `true` | Cheaper stage nodes (may be reclaimed) |
| `node_disk_size_gb` | `30` | Small boot disk; avoids fresh-project SSD quota surprises |
| `node_disk_type` | `pd-standard` | Standard disk for lab quota/cost |
| `artifact_registry_repository_id` | `spaceops` | AR repo ID |
| `deploy_service_account_id` | `spaceops-deploy` | Deploy SA short name |
| `enable_apis` | `true` | Enable Container + AR APIs |

Copy `terraform.tfvars.example` → `terraform.tfvars` (gitignored) and set `project_id`.

## State backend

**Local (default):** `terraform apply` writes `terraform.tfstate` locally — fine for one engineer
testing; **do not commit** state files.

**Remote (recommended for shared stage):**

1. Create a versioned GCS bucket (one-time):

   ```bash
   export PROJECT_ID=your-gcp-project-id
   gcloud storage buckets create gs://${PROJECT_ID}-terraform-state \
     --project="${PROJECT_ID}" --location=us-central1 --uniform-bucket-level-access
   gcloud storage buckets update gs://${PROJECT_ID}-terraform-state --versioning
   ```

2. Uncomment the `backend "gcs"` block in `versions.tf` and set bucket/prefix.

3. `terraform init -migrate-state`

## Cost estimate (stage, us-central1, 2026 list prices — verify in console)

Rough **always-on** monthly cost for defaults (`1 × e2-standard-2` preemptible, no GPU):

| Component | Estimate (USD/mo) | Notes |
|-----------|-------------------|--------|
| GKE management fee | ~$73 | Per cluster (regional) |
| Compute (preemptible e2-standard-2) | ~$15–25 | 1 node; varies by uptime |
| Persistent disks (Helm Postgres PVC) | ~$1–5 | 10Gi `values-stage.yaml` |
| Artifact Registry storage | ~$0–5 | Depends on image retention |
| Egress / LB | ~$5–20 | If `LoadBalancer` exposed |
| **Total (order of magnitude)** | **~$95–130/mo** | Scale down via PS6.9 |

**Cost reduction:**

- Set `node_count = 0` is **not** supported on default pool — use [PS6.9 billing controls](../../../roadmap/02-production-scale/sprint-6/PS6.9-billing-shutdown-controls.md) (scheduled scale-down / cluster stop).
- `preemptible_nodes = true` (default) vs standard saves ~60–70% on compute.
- Destroy cluster when idle: `terraform destroy` (see below).

**Infra $ vs model $:** GKE cost is separate from [LLM token budget](../../../docs/runbooks/llm_cost_guardrails.md) (PS5.6). Platform guardrails: [cloud_cost_hygiene.md](../../../docs/runbooks/cloud_cost_hygiene.md) (PS6.9).

## Deploy / destroy flow

### Validate (no GCP credentials)

```bash
cd infra/terraform/gcp
terraform init -backend=false
terraform validate
```

Or from repo root: `make terraform-gcp-validate`

### Apply (live GCP — stretch)

```bash
cd infra/terraform/gcp
cp terraform.tfvars.example terraform.tfvars   # edit project_id
terraform init
terraform plan
terraform apply
```

Capture outputs:

```bash
terraform output get_credentials_command
terraform output artifact_registry_repository
```

Then follow [gcp_stage_deploy.md](../../../docs/runbooks/gcp_stage_deploy.md) for kubectl, images, Helm.

### Troubleshooting (live apply)

| Error | Fix |
|-------|-----|
| `invalid_rapt` / OAuth | `gcloud auth login` then `gcloud auth application-default login` |
| Budget API **quota project** | Provider sets `billing_project` in `versions.tf`; also run `gcloud auth application-default set-quota-project PROJECT_ID` |
| **Identity Pool does not exist** (ESO WI) | Fixed: WI binding runs after GKE cluster (`depends_on`) |
| **deletion_protection** blocks replace/destroy | Set `deletion_protection = false` in tfvars (default); or `gcloud container clusters update CLUSTER --region=REGION --no-deletion-protection` |
| Cluster **tainted** after failed apply | If cluster is healthy: `terraform untaint google_container_cluster.primary` then `apply` (avoids recreate) |
| Budget **400 invalid argument** | `budget.tf` strips any `billingAccounts/` prefix before passing `billing_account_id` to the provider, uses project number, and avoids unsupported label filters |
| Budget **400 invalid argument** with valid account | Set `budget_currency_code` to billing account currency (`gcloud billing accounts describe ... --format="value(currencyCode)"`) |
| **SSD_TOTAL_GB exceeded** | Broken regional default pool can exceed quota. Defaults now use one node zone plus `pd-standard` 30GB for the temporary default pool; delete the broken `ERROR` cluster and re-apply. |
| Budget optional for lab | Set `enable_budget_alert = false` in `terraform.tfvars` |

After a failed apply, run `terraform apply` again (or `terraform destroy` to reset).

### Destroy

```bash
terraform destroy
```

**Time-box target (stretch acceptance):** one engineer should recreate stage from this README +
runbook in under ~45 minutes (excluding secret bootstrap and first image build).

## Portability

- Same Helm chart and `values-stage.yaml` as local kind (PS6.3).
- Optional `values-gcp-stage.yaml` only overrides image registry host.
- Replace this Terraform with another cloud module without changing application code.
- Optional GitOps: [Argo CD bootstrap](../../../docs/runbooks/gitops_bootstrap.md) (PS6.7).

## Cloud Run fallback (showcase only)

For API-only demos without in-cluster Postgres/NATS, Cloud Run can host the FastAPI container
with Cloud SQL / managed services — **not** implemented in PS6.8. See Phase 7 portfolio notes in
ADR 0009.

## CI

- **PR gate:** `.github/workflows/gcp-terraform-validate.yml` — `terraform validate`
- **Manual image push:** `.github/workflows/gcp-artifact-registry-push.yml` — `workflow_dispatch`

## Related

- [PS6.8 spec](../../../roadmap/02-production-scale/sprint-6/PS6.8-gcp-baseline-deploy-plan.md)
- [PS6.9 billing controls](../../../roadmap/02-production-scale/sprint-6/PS6.9-billing-shutdown-controls.md)
- [Cloud cost hygiene runbook](../../../docs/runbooks/cloud_cost_hygiene.md)
- [Secrets bootstrap (ESO/GSM)](../../../docs/runbooks/k8s_secrets_bootstrap.md)

## Billing budget (PS6.9)

Optional `budget.tf` — set `enable_budget_alert = true` and `billing_account_id` in `terraform.tfvars`.
`billing_account_id` may be either `012345-678901-ABCDEF` or `billingAccounts/012345-678901-ABCDEF`;
the Terraform module passes the short ID to the Google provider.
Set `budget_currency_code` to the billing account currency (`PLN` for the current lab account).
See [cloud_cost_hygiene.md](../../../docs/runbooks/cloud_cost_hygiene.md) for gcloud stubs and scale-down scripts.
