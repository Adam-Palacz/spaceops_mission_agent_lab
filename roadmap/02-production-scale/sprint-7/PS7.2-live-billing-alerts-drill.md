# PS7.2 — Live billing alerts + cost drill

| **Task ID** | PS7.2 | **Status** | Done |

## Description

PS6.9 stretch: wire budget alert in GCP, run one shutdown/scale-down drill, and record the dated
evidence in the cost runbook.

## Requirements

- [x] Terraform budget alert applies successfully in the live stage project.
- [x] Billing account format is documented as the short ID in Terraform input, with full `billingAccounts/...` accepted only if normalized.
- [x] Budget currency matches the billing account currency (for the current lab account: `PLN`).
- [x] Shutdown/scale-down drill is run once against the stage cluster or documented as skipped with reason.

## Acceptance

- [x] Budget alert exists in GCP with project scope and notification channel.
- [x] `docs/runbooks/cloud_cost_hygiene.md` has the drill date, operator, and outcome.
- [x] Failure modes are covered: Budget API 400, billing account currency mismatch, and project number vs project ID filter.
- [x] If live budget creation is blocked by org/billing permissions, `enable_budget_alert=false` is documented as a temporary bypass and the blocker is recorded.

## Completion evidence (2026-06-14)

- **Project:** `spaceops-project-498213` (number `78972438155`)
- **Terraform:** `enable_budget_alert = true`, `billing_account_id = "01F5D6-1CDDB6-32152A"`, `budget_currency_code = "PLN"`, cap `50`
- **Budget:** `spaceops-stage-monthly` — `gcloud billing budgets list --billing-account=01F5D6-1CDDB6-32152A`
- **Filter:** `projects/78972438155` (project number via `data.google_project.current[0].number`)
- **Notification:** email → `adam.palacz96@gmail.com`
- **Scale-down drill:** `make cloud-scale-down-check` (dry-run) → node pool `spaceops-stage-pool` **1 → 0 → 1** via `scripts/cloud/schedule_scale_down.py`
- **Full shutdown drill:** `make gcp-stage-down` (2026-06-14) — Helm + `terraform destroy` (19 resources); current teardown restores the persistent budget alert afterward
- **Live re-verification:** 2026-06-15 — budget restored with targeted Terraform apply; no GKE clusters recreated

## Operator quick path

```powershell
$env:GCP_PROJECT_ID = "spaceops-project-498213"
cd infra/terraform/gcp
terraform apply -auto-approve
terraform output budget_enabled
cd ../../..

make cloud-scale-down-check
.venv\Scripts\python.exe scripts/cloud/schedule_scale_down.py --project $env:GCP_PROJECT_ID --nodes 0
.venv\Scripts\python.exe scripts/cloud/schedule_scale_down.py --project $env:GCP_PROJECT_ID --nodes 1
make gcp-stage-down
```

Runbook: [cloud_cost_hygiene.md](../../../docs/runbooks/cloud_cost_hygiene.md) §3b.

`make gcp-stage-down` preserves the live budget alert by restoring only
`google_billing_budget.spaceops` after the ephemeral stage stack is destroyed. Use
`GCP_STAGE_DOWN_ARGS="--confirm --terraform-auto-approve --destroy-budget-alert"` only when the
project/account is being retired.

## Implementation notes (repo)

| Artifact | Purpose |
|----------|---------|
| `infra/terraform/gcp/budget.tf` | Budget + email notification channel |
| `scripts/cloud/schedule_scale_down.py` | Node pool resize (Windows `resolve_tool` for gcloud) |
| `Makefile` `cloud-scale-down-check` | Dry-run wrapper |
| `docs/runbooks/cloud_cost_hygiene.md` | Failure modes + PS7.2 drill log |
