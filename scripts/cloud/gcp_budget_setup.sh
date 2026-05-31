#!/usr/bin/env bash
# PS6.9 — create a GCP billing budget with email alerts (gcloud stub).
# Prefer Terraform: infra/terraform/gcp/budget.tf (enable_budget_alert = true).
set -euo pipefail

DRY_RUN=0
BILLING_ACCOUNT_ID="${BILLING_ACCOUNT_ID:-}"
PROJECT_ID="${GCP_PROJECT_ID:-}"
BUDGET_USD="${BUDGET_AMOUNT_USD:-150}"
ALERT_EMAIL="${BUDGET_ALERT_EMAIL:-}"

usage() {
  cat <<'EOF'
Usage: gcp_budget_setup.sh [--dry-run]

Environment:
  BILLING_ACCOUNT_ID   Required (e.g. 012345-678901-ABCDEF)
  GCP_PROJECT_ID       Required
  BUDGET_AMOUNT_USD    Monthly cap (default 150)
  BUDGET_ALERT_EMAIL   Required for notifications

See docs/runbooks/cloud_cost_hygiene.md
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ "$DRY_RUN" -eq 1 ]]; then
  BILLING_ACCOUNT_ID="${BILLING_ACCOUNT_ID:-012345-678901-ABCDEF}"
  PROJECT_ID="${PROJECT_ID:-your-gcp-project-id}"
  ALERT_EMAIL="${ALERT_EMAIL:-you@example.com}"
fi

if [[ -z "$BILLING_ACCOUNT_ID" || -z "$PROJECT_ID" || -z "$ALERT_EMAIL" ]]; then
  echo "Set BILLING_ACCOUNT_ID, GCP_PROJECT_ID, and BUDGET_ALERT_EMAIL." >&2
  echo "Dry-run example:" >&2
  echo "  BILLING_ACCOUNT_ID=012345-678901-ABCDEF GCP_PROJECT_ID=my-proj BUDGET_ALERT_EMAIL=you@example.com $0 --dry-run" >&2
  exit 1
fi

CMD=(
  gcloud billing budgets create
  "--billing-account=${BILLING_ACCOUNT_ID}"
  "--display-name=spaceops-${PROJECT_ID}-monthly"
  "--budget-amount=${BUDGET_USD}USD"
  "--filter-projects=projects/${PROJECT_ID}"
  "--threshold-rule=percent=0.5,basis=current-spend"
  "--threshold-rule=percent=0.9,basis=current-spend"
  "--threshold-rule=percent=1.0,basis=forecasted-spend"
  "--notifications-rule=pubsub-topic=projects/${PROJECT_ID}/topics/billing-alerts"
  "--notifications-rule=schema-version=1.0"
)

echo "NOTE: gcloud budget email routing often needs a Pub/Sub topic + Cloud Function or"
echo "      Billing export. For email-only alerts, use Terraform budget.tf (PS6.9) instead."
echo "project=${PROJECT_ID} billing_account=${BILLING_ACCOUNT_ID} budget_usd=${BUDGET_USD} email=${ALERT_EMAIL}"

if [[ "$DRY_RUN" -eq 1 ]]; then
  printf 'would_run: %q ' "${CMD[@]}"
  echo
  exit 0
fi

echo "Creating budget (ensure billingbudgets API is enabled)..."
"${CMD[@]}"
