# PS7.2 — Live billing alerts + cost drill

| **Task ID** | PS7.2 | **Status** | Todo |

## Description

PS6.9 stretch: wire budget alert in GCP, run one shutdown/scale-down drill, and record the dated
evidence in the cost runbook.

## Requirements

- [ ] Terraform budget alert applies successfully in the live stage project.
- [ ] Billing account format is documented as the short ID in Terraform input, with full `billingAccounts/...` accepted only if normalized.
- [ ] Budget currency matches the billing account currency (for the current lab account: `PLN`).
- [ ] Shutdown/scale-down drill is run once against the stage cluster or documented as skipped with reason.

## Acceptance

- [ ] Budget alert exists in GCP with project scope and notification channel.
- [ ] `docs/runbooks/cloud_cost_hygiene.md` has the drill date, operator, and outcome.
- [ ] Failure modes are covered: Budget API 400, billing account currency mismatch, and project number vs project ID filter.
- [ ] If live budget creation is blocked by org/billing permissions, `enable_budget_alert=false` is documented as a temporary bypass and the blocker is recorded.
