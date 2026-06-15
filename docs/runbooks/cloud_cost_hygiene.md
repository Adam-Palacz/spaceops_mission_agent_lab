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
budget_currency_code  = "PLN"                    # must match billing account currency
budget_alert_emails   = ["you@example.com"]
```

`billing_account_id` can also be the full `billingAccounts/012345-678901-ABCDEF` resource name;
Terraform strips that prefix before passing the value to the Google provider.

Then:

```bash
cd infra/terraform/gcp
terraform apply
cd ../../..
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

### Failure modes (budget Terraform)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Budget API **400 invalid argument** | `billing_account_id` passed as full `billingAccounts/...` without normalization | Use short ID `012345-678901-ABCDEF` in `terraform.tfvars`; module strips prefix via `replace(var.billing_account_id, "billingAccounts/", "")` |
| Budget API **400** with valid account | `budget_currency_code` ≠ billing account currency | `gcloud billing accounts describe BILLING_ACCOUNT_ID --format="value(currencyCode)"` — lab account uses **PLN** |
| Budget API **400** on `projects` filter | Project **ID** used instead of project **number** | `budget.tf` uses `data.google_project.current[0].number` → `projects/78972438155` |
| Budget create blocked (org policy / IAM) | Operator lacks `billing.budgets.create` | Set `enable_budget_alert = false` temporarily; record blocker in PR/spec; fix IAM or use Console |

**Temporary bypass:** `enable_budget_alert = false` in `terraform.tfvars` — skips budget + notification channel resources; GKE/AR still apply.

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
3. Alternative: **full stage teardown** `make gcp-stage-down` Fri PM / `make gcp-stage-up` Mon AM
   for lab projects. The wrapper restores the persistent budget alert after destroying stage resources.

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

## 3b. PS7.2 live drill log (dated evidence)

| Field | Value |
|-------|--------|
| **Date** | 2026-06-14 |
| **Operator** | adam.palacz96@gmail.com |
| **Project** | `spaceops-project-498213` (number `78972438155`) |
| **Outcome** | PASS — budget alert live + node-pool scale-down drill executed |

**Budget alert (Terraform):**

- `terraform apply` with `enable_budget_alert = true`, `billing_account_id = "01F5D6-1CDDB6-32152A"`, `budget_currency_code = "PLN"`, `budget_amount_usd = 50`
- Budget: `spaceops-stage-monthly` — thresholds 50% / 90% current spend, 100% forecast
- Filter: `projects/78972438155` (project number, not project ID)
- Notification: email channel → `adam.palacz96@gmail.com`
- Verify: `gcloud billing budgets list --billing-account=01F5D6-1CDDB6-32152A`
- `terraform output budget_enabled` → `true`

**Scale-down drill (node pool):**

```powershell
$env:GCP_PROJECT_ID = "spaceops-project-498213"
make cloud-scale-down-check   # dry-run: resize --num-nodes 0
.venv\Scripts\python.exe scripts/cloud/schedule_scale_down.py --project spaceops-project-498213 --nodes 0
.venv\Scripts\python.exe scripts/cloud/schedule_scale_down.py --project spaceops-project-498213 --nodes 1
```

Result: `spaceops-stage-pool` resized **1 → 0 → 1** successfully (~3 min down, ~1 min up).

**Full shutdown drill (PS7.1/PS7.2):** `make gcp-stage-down` removes Helm workloads + ephemeral
Terraform resources, then restores the persistent budget alert. The original drill executed
2026-06-14 after the live demo and removed 19 resources — post-check: no GKE clusters, no AR repos.
Use `--destroy-budget-alert` only when retiring the project/account.

**Live re-verification (2026-06-15):** budget `spaceops-stage-monthly` restored with targeted
Terraform apply; GKE cluster list remained empty.

---

## 4. Cost estimate reference (stage)

See [infra/terraform/gcp/README.md](../../infra/terraform/gcp/README.md) — order of magnitude **~$95–130/mo**
always-on (1 preemptible `e2-standard-2`, regional GKE). Tactics:

- `preemptible_nodes = true` (PS6.8 default)
- Overnight node pool → 0
- `make gcp-stage-down` when lab compute is idle; add `--destroy-budget-alert` only at project retirement
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
- [PS7.2 live drill spec](../../roadmap/02-production-scale/sprint-7/PS7.2-live-billing-alerts-drill.md)
