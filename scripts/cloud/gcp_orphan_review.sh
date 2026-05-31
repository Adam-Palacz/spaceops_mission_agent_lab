#!/usr/bin/env bash
# PS6.9 — monthly orphan resource review (list-only stub).
set -euo pipefail

DRY_RUN=1
PROJECT_ID="${GCP_PROJECT_ID:-}"

usage() {
  cat <<'EOF'
Usage: gcp_orphan_review.sh [--execute]

Lists candidate orphan resources (disks, addresses, forwarding rules).
Default is dry-run/list only. --execute only runs read-only gcloud list commands.

Set GCP_PROJECT_ID. See docs/runbooks/cloud_cost_hygiene.md
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute) DRY_RUN=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$PROJECT_ID" ]]; then
  echo "Set GCP_PROJECT_ID." >&2
  exit 1
fi

run_list() {
  local title="$1"
  shift
  echo ""
  echo "=== ${title} ==="
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf 'would_run: %q\n' "$@"
  else
    "$@"
  fi
}

echo "PS6.9 orphan review project=${PROJECT_ID} mode=$([[ $DRY_RUN -eq 1 ]] && echo dry-run || echo list)"

run_list "Unattached disks (review manually)" \
  gcloud compute disks list --project="$PROJECT_ID" \
  --filter="NOT users:*" --format="table(name,zone,sizeGb,status)"

run_list "Reserved static IPs without users" \
  gcloud compute addresses list --project="$PROJECT_ID" \
  --filter="status=RESERVED" --format="table(name,region,address,status)"

run_list "Forwarding rules (check unused LBs)" \
  gcloud compute forwarding-rules list --project="$PROJECT_ID" \
  --format="table(name,region,IPAddress,target)"

run_list "GKE clusters" \
  gcloud container clusters list --project="$PROJECT_ID" \
  --format="table(name,location,currentNodeCount,status)"

echo ""
echo "Artifact Registry: review old image tags in Console → Artifact Registry → spaceops"
echo "Done. Delete orphans manually or via targeted gcloud delete commands."
