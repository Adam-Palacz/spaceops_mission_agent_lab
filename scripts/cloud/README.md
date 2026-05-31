# Cloud cost scripts (PS6.9)

Optional **stubs** for GCP billing and scale-down hygiene. Not run in CI; require `gcloud` and a live project.

| Script | Purpose |
|--------|---------|
| `schedule_scale_down.sh` / `.ps1` | Resize GKE node pool (overnight scale-down) |
| `gcp_budget_setup.sh` | gcloud budget create stub (prefer Terraform) |
| `gcp_orphan_review.sh` | Monthly orphan disk/IP/LB listing |

Runbook: [docs/runbooks/cloud_cost_hygiene.md](../../docs/runbooks/cloud_cost_hygiene.md)

Terraform budget (recommended): `infra/terraform/gcp/budget.tf` with `enable_budget_alert = true`.
