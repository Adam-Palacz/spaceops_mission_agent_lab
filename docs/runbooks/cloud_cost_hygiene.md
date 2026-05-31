# Cloud cost hygiene runbook (PS6.9)

Platform-level **cost guardrails** for GCP stage/prod: budgets, alerts, scheduled scale-down, and
orphan cleanup. Complements host-side [GPU cost hygiene](gpu_cost_hygiene.md) (PS5.7 compose/NIM idle
TTL) with **infra $** controls in the cloud.

**Related:** [GCP stage deploy](gcp_stage_deploy.md) (PS6.8),
[infra/terraform/gcp/README.md](../../infra/terraform/gcp/README.md),
[LLM cost guardrails](llm_cost_guardrails.md) (PS5.6 **model $**).

---

## Two cost layers (do not conflate)

| Layer | What it controls | Where | PS |
|-------|------------------|-------|-----|
| **Infra $** | GKE, disks, LB, Artifact Registry, egress | This runbook + Terraform | PS6.9 |
| **Model $** | OpenAI / NIM token usage per run/day | `LLM_DAILY_TOKEN_BUDGET`, `LLMBudgetExceededError` | PS5.6 |

Stopping a GKE cluster does **not** stop OpenAI charges if something still calls the API. Raising
`LLM_DAILY_TOKEN_BUDGET` does **not** cap GKE management fees. Operators need both playbooks.

**Local lab GPU/NIM:** see [gpu_cost_hygiene.md](gpu_cost_hygiene.md) — `make gpu-down`, idle TTL.
**Cloud GPU/NIM:** **not enabled by default** (Phase 7); PS6.8 Terraform has **no GPU node pool**.

---

## Labeling for cost allocation

All SpaceOps Terraform resources apply:

| Label | Values | Purpose |
|-------|--------|---------|
| `env` | `dev`, `stage`, `prod` | Billing breakdown / budget filters |
| `app` | `spaceops` | Product slice |
| `managed_by` | `terraform` | Orphan detection |

Helm/K8s workloads should mirror `env` via `isolation.environment` in values overlays (PS6.5).

**GCP Console:** Billing → Reports → Group by **Label** → `env`.

---

## 1. Budget alert (GCP)

### Option A — Terraform (recommended when using PS6.8 stack)

Enable in `terraform.tfvars`:

```hcl
enable_budget_alert   = true
billing_account_id    = "012345-678901-ABCDEF"   # Billing → Account management
budget_amount_usd     = 150
budget_alert_emails   = ["you@example.com"]
```

Then:

```bash
cd infra/terraform/gcp
terraform apply
```

Creates a monthly project budget with 50% / 90% / 100% thresholds and email notification channels.
Requires `billingbudgets.googleapis.com` and `monitoring.googleapis.com` (enabled when budget alert is on).

### Option B — gcloud stub (no Terraform)

```bash
scripts/cloud/gcp_budget_setup.sh --dry-run
# Edit BILLING_ACCOUNT_ID and emails in the script, then:
scripts/cloud/gcp_budget_setup.sh
```

### Stretch acceptance

Wire budget in a live stage project; attach screenshot or `terraform output` reference in PR.

---

## 2. Cluster scale-down (non-prod overnight)

Goal: stop paying for compute when stage is unused. GKE **management fee** (~$73/mo regional) still
applies while the cluster exists — scale-to-zero nodes reduces compute, not always the full cluster fee.

### Manual / cron (documented stubs)

**Dry-run (shows planned gcloud command):**

```bash
scripts/cloud/schedule_scale_down.sh --dry-run
```

**Scale node pool to 0 (after draining / outside work hours):**

```bash
export GCP_PROJECT_ID=your-project
export GCP_REGION=us-central1
export GKE_CLUSTER=spaceops-stage
export GKE_NODE_POOL=spaceops-stage-pool
scripts/cloud/schedule_scale_down.sh --nodes 0
```

**Restore for work hours:**

```bash
scripts/cloud/schedule_scale_down.sh --nodes 1
```

PowerShell: `scripts/cloud/schedule_scale_down.ps1 -DryRun`

Make wrapper: `make cloud-scale-down-check`

### Scheduled automation (stretch)

1. **Cloud Scheduler** → HTTP target or **Cloud Run job** invoking scale-down script with SA that has
   `container.developer`.
2. **Scale-up** job before business hours (e.g. 08:00 UTC).
3. Alternative: **full teardown** `terraform destroy` Fri PM / `terraform apply` Mon AM for lab projects.

### Before scale-down

1. Confirm no active demos / Argo CD sync needed overnight.
2. Optional: `kubectl drain` nodes or accept pod eviction on non-prod.
3. Postgres PVC persists — you still pay for disk (~$1–5/mo per 10Gi).

### PS5.7 alignment

| PS5.7 (compose) | PS6.9 (cloud) |
|-----------------|---------------|
| Host idle TTL stops `nim-llm` container | Node pool resize / cluster stop |
| Activity file `./var/llm_last_gpu_call_at` | No GPU pool in PS6 — NIM not deployed on GKE by default |
| `make gpu-idle-check` | `make cloud-scale-down-check` |

---

## 3. Monthly orphan review checklist

Run monthly (or after each sprint) on stage/dev projects:

| Item | Command / action |
|------|------------------|
| Unattached persistent disks | `gcloud compute disks list --filter='NOT users:*' --format='table(name,zone,sizeGb,status)'` — delete orphans |
| Unused static IPs | `gcloud compute addresses list --filter='status=RESERVED AND users:*'` |
| Old Artifact Registry images | Console → Artifact Registry → `spaceops` → delete tags older than 90d |
| Idle GKE clusters | List clusters; destroy lab clusters not used in 30d |
| Secret Manager versions | Prune disabled old versions if rotation policy allows |
| Load balancers | `gcloud compute forwarding-rules list` — remove unused rules |

Script stub (dry-run lists only):

```bash
scripts/cloud/gcp_orphan_review.sh --dry-run
```

Record review date in team notes or PR when executed (stretch acceptance).

---

## 4. Cost estimate reference (stage)

See [infra/terraform/gcp/README.md](../../infra/terraform/gcp/README.md) — order of magnitude **~$95–130/mo**
always-on (1 preemptible `e2-standard-2`, regional GKE). Tactics:

- `preemptible_nodes = true` (PS6.8 default)
- Overnight node pool → 0
- `terraform destroy` when lab complete
- Budget alert at 50% / 90%

---

## 5. Incident: budget alert fired

1. **Identify layer** — Billing report: GKE vs AR vs networking vs **API (external)**.
2. **Infra** — Run orphan checklist; scale down node pool; confirm no duplicate clusters.
3. **Model $** — Follow [llm_cost_guardrails.md](llm_cost_guardrails.md); check `llm_tokens_total`.
4. **Do not** disable budget alerts without setting a replacement threshold.
5. Escalate if forecast exceeds project cap before month end.

---

## 6. Out of scope (PS6.9)

- FinOps SaaS dashboards (Cloudability, etc.)
- Hard spending caps enforced in application code
- Org-policy deny-all billing (requires org admin)

---

## Cross-links

- [GPU cost hygiene (local compose)](gpu_cost_hygiene.md)
- [LLM cost guardrails (token budget)](llm_cost_guardrails.md)
- [GCP stage deploy](gcp_stage_deploy.md)
- [PS6.9 spec](../../roadmap/02-production-scale/sprint-6/PS6.9-billing-shutdown-controls.md)
