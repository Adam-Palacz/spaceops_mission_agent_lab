# Runbook — GCP stage deploy (PS6.8)

Deploy SpaceOps to a **small GKE stage cluster** using the same Helm chart and `values-stage.yaml`
overlays as local kind. This is the **stretch** acceptance path; minimum PS6.8 DoD is Terraform
validate + documentation only.

**Related:** [ADR 0009](../adr/0009-gcp-baseline-portable-first.md),
[infra/terraform/gcp/README.md](../../infra/terraform/gcp/README.md),
[PS6.9 billing controls](../../roadmap/02-production-scale/sprint-6/PS6.9-billing-shutdown-controls.md),
[stage operating policy](stage_operating_policy.md)

---

## Prerequisites

| Item | Notes |
|------|--------|
| GCP project | Billing enabled; `gcloud auth login` |
| Terraform ≥ 1.5 | See `infra/terraform/gcp/` |
| `gcloud`, `kubectl`, `helm`, `docker` | Same versions as local K8s runbooks |
| Secrets in GSM | Per [k8s_secrets_bootstrap.md](k8s_secrets_bootstrap.md) + ESO example |
| **No GKE-only app code** | API/MCP containers unchanged from compose/kind |

---

## Quick path

Stage is **ephemeral by default** per [stage_operating_policy.md](stage_operating_policy.md). Before
bringing it up, record the owner and teardown time; use a long-lived window only for soak, game day,
or external review evidence.

Bring up the full stage stack and validate smoke + scenarios A/B:

```powershell
$env:GCP_PROJECT_ID = "spaceops-project-498213"
$env:GCP_IMAGE_TAG = "stage"
make gcp-stage-up
```

This runs:

```text
terraform init && terraform apply -auto-approve
make gcp-stage-images
make gcp-stage-deploy
make gcp-stage-smoke
make gcp-stage-demo
```

Tear everything down again:

```powershell
$env:GCP_PROJECT_ID = "spaceops-project-498213"
make gcp-stage-down
```

Use the numbered sections below for debugging or partial recovery.

---

## 0. kubectl access to GKE (before deploy)

If `make gcp-stage-deploy` fails with `failed to download openapi` or `connectex` to the
control plane IP (`35.x.x.x:443`), refresh credentials — the kubeconfig endpoint is stale or
you are not authenticated.

```powershell
$env:GCP_PROJECT_ID = "spaceops-project"
make gcp-kube-credentials
kubectl get nodes
```

Manual:

```bash
gcloud auth login
gcloud auth application-default login
gcloud container clusters get-credentials spaceops-stage --region us-central1 --project spaceops-project
kubectl cluster-info
```

If the cluster does not exist, run section **1** (Terraform) first. If the cluster exists but
Terraform state is empty, see targeted apply in section **2** — do not assume deploy works without
a reachable API.

If `kubectl` reports an unreachable OpenAPI endpoint but `gcloud container clusters list` shows no
`spaceops-stage`, kubeconfig points at a deleted cluster. Stop the deploy; recreate/import the
cluster first, then refresh credentials. Do not run secrets bootstrap or Helm against a stale context.

---

## 1. Provision infrastructure

```bash
cd infra/terraform/gcp
cp terraform.tfvars.example terraform.tfvars   # set project_id
terraform init
terraform plan
terraform apply
terraform state list
```

Save outputs:

```bash
terraform output -json > /tmp/spaceops-gcp-outputs.json
eval "$(terraform output -raw get_credentials_command)"
terraform output artifact_registry_repository
terraform output eso_service_account_email
```

Do not build/push images until `terraform state list` includes
`google_artifact_registry_repository.spaceops` and `terraform output artifact_registry_repository`
prints the repository path expected by the image push step.

**Validate-only (no GCP):** `make terraform-gcp-validate`

---

## 2. Build and push images (Artifact Registry)

Images must include `data/telemetry/*.ndjson` for MCP queries on GKE (see root `.dockerignore` PS7.1).

**Order:** section **1** (Terraform) must create the AR repo **before** `make gcp-stage-images`.

**Automated:**

```bash
export GCP_PROJECT_ID=your-gcp-project-id
export GCP_REGION=us-central1
export GCP_IMAGE_TAG=stage
make gcp-stage-images
```

PowerShell:

```powershell
$env:GCP_PROJECT_ID = "spaceops-project"
make gcp-stage-images
```

If this fails with `Repository "spaceops" not found`, the Artifact Registry repository does not exist
in the selected project/region or the repository ID differs. Run `terraform apply` first and verify:

```bash
cd infra/terraform/gcp
terraform state list
terraform output artifact_registry_repository
gcloud artifacts repositories list --project="$GCP_PROJECT_ID" --location="$GCP_REGION"
```

If `terraform state list` is empty but a live cluster already exists, avoid a blind full apply because
Terraform may try to create or replace existing resources. Reconcile/import the live resources, or
create only the missing image-push prerequisite first:

```bash
terraform apply \
  -target=google_project_service.apis \
  -target=google_artifact_registry_repository.spaceops \
  -target=google_project_iam_member.gke_nodes_ar_reader
```

From repo root the same targeted recovery is available as:

```bash
make gcp-terraform-ar
```

**Manual:**

```bash
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1
export AR_REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/spaceops"
export TAG=stage

gcloud auth configure-docker "${REGION}-docker.pkg.dev"

docker build -t "${AR_REPO}/api:${TAG}" -f apps/api/Dockerfile .
docker build -t "${AR_REPO}/mcp:${TAG}" -f apps/mcp/Dockerfile .
docker push "${AR_REPO}/api:${TAG}"
docker push "${AR_REPO}/mcp:${TAG}"
```

**CI alternative:** GitHub Actions → **GCP Artifact Registry push** (`workflow_dispatch`) when
`GCP_PROJECT_ID` and `GCP_SA_KEY` (or WIF) secrets are configured.

---

## 3. Bootstrap secrets (GSM + ESO)

1. Create secrets in Google Secret Manager matching `values-stage.yaml` `externalSecrets.remoteRefs`
   (e.g. `spaceops-stage/postgres-password`).
2. Install External Secrets Operator and apply
   `deploy/examples/secrets/eso/secret-store-gcp-sm.yaml.example` (annotate K8s SA with
   `eso_service_account_email` from Terraform).
3. See [k8s_secrets_bootstrap.md](k8s_secrets_bootstrap.md) for key names and Helm `existingSecret`.

**Local dev shortcut (not for shared stage):** `make k8s-secrets-bootstrap` with imperative Secret —
only for throwaway clusters.

---

## 4. Install Helm (portability proof)

Same chart as PS6.2 / PS6.3; stage overlay + GCP image hosts.

**Automated (recommended):** full in-cluster MCP stack (`values-stage-full.yaml`) + secrets bootstrap:

```powershell
# From repo root — load secrets from .env
Get-Content .env | ForEach-Object {
  if ($_ -match '^\s*(POSTGRES_PASSWORD|OPENAI_API_KEY)\s*=\s*(.+)\s*$') {
    Set-Item -Path "env:$($matches[1])" -Value $matches[2].Trim('"')
  }
}
$env:GCP_PROJECT_ID = "spaceops-project"
$env:K8S_NAMESPACE = "spaceops-stage"
make gcp-stage-deploy
```

**Manual Helm** (namespace pre-created → `global.createNamespace=false`):

```bash
export NAMESPACE=spaceops-stage
export AR_REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/spaceops"

helm upgrade --install spaceops deploy/helm/spaceops \
  --namespace "${NAMESPACE}" \
  -f deploy/helm/spaceops/values.yaml \
  -f deploy/helm/spaceops/values-stage.yaml \
  -f deploy/helm/spaceops/values-stage-full.yaml \
  -f deploy/helm/spaceops/values-gcp-stage.yaml \
  --set global.createNamespace=false \
  --set images.api.repository="${AR_REPO}/api" \
  --set images.mcp.repository="${AR_REPO}/mcp" \
  --set images.api.tag=stage \
  --set images.mcp.tag=stage \
  --wait --timeout 15m
```

**Postgres on GCE PD:** chart sets `postgres.dataDir=/var/lib/postgresql/data/pgdata` (required — PD mount
includes `lost+found` at volume root).

**Database schema:** after first install, `make gcp-stage-deploy` runs `alembic upgrade head` via the API
pod (creates `telemetry_events`, `dlq_events`, checkpoint tables). If persister is in `CrashLoopBackOff`
with `relation "dlq_events" does not exist`, run migrations manually:

```bash
kubectl exec -n spaceops-stage deploy/spaceops-api -- python -m alembic upgrade head
kubectl rollout restart deploy/spaceops-telemetry-persister -n spaceops-stage
```

Verify:

```bash
make gcp-stage-status
make gcp-stage-smoke
# or:
curl -s "http://$(kubectl get svc spaceops-api -n spaceops-stage -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):8000/health"
```

**Full stack on GKE (what `values-stage-full.yaml` adds):**

| Component | In stage baseline | In stage-full |
|-----------|-------------------|---------------|
| api, postgres, opa, nats, persister | yes | yes |
| telemetry-mcp | yes | yes |
| kb-mcp, ticket-mcp, gitops-mcp | no | **yes** |
| jaeger, otel-collector | yes | yes |
| prometheus / grafana / postgres-exporter | no | optional via `values-monitoring-stage.yaml` (PR1.1) |
| nim / GPU | no | no (Phase 7; use laptop NIM hybrid) |
| UI | no | no (compose-only; PS6.2 scope) |

---

## 5. Ingress and TLS (lab posture)

| Approach | PS6.8 default | Production follow-up |
|----------|---------------|----------------------|
| **LoadBalancer Service** | Yes (`values-gcp-stage.yaml`) | Replace with Ingress + static IP |
| **TLS** | **Deferred** — HTTP only for lab | cert-manager + Let's Encrypt or Google-managed cert |
| **GKE Ingress** | Documented alternative | `ingress.enabled` in future Helm profile |

For portfolio demos, HTTP to LoadBalancer IP is acceptable; do not expose prod without TLS.

---

## 6. Optional GitOps (PS6.7)

**Status today:** your live GKE cluster was installed with **imperative Helm** (`helm upgrade` /
`make gcp-stage-deploy`). **Argo CD is not installed yet** — GitOps is optional (PS6.7), documented
and ready, but not required for the portfolio demo.

### Imperative vs GitOps

| Path | When | Command |
|------|------|---------|
| **Imperative** (current) | Lab, first deploy, debugging | `make gcp-stage-deploy` |
| **GitOps** | Ongoing stage sync from Git | `make gitops-install` + `make gitops-bootstrap` |

Do **not** run both on the same release — pick one owner for `spaceops` in `spaceops-stage`.
The ownership and drift-detection rules are defined in
[stage_operating_policy.md](stage_operating_policy.md).

### Enable Argo CD on this GKE cluster

1. **Push** this repo (including `deploy/gitops/`) to GitHub.
2. **Secrets** stay out of Git — keep `spaceops-stage-secrets` (PS6.6 bootstrap or GSM+ESO).
3. Edit `deploy/gitops/argocd/applications/values.yaml` for GKE:

   ```yaml
   gcp:
     enabled: true
     region: us-central1
     projectId: spaceops-project
     imageTag: stage
   ```

4. Install and bootstrap:

   ```bash
   export GITOPS_REPO_URL=https://github.com/YOUR_ORG/spaceops_mission_agent_lab.git
   make gitops-install
   make gitops-bootstrap
   make gitops-status
   ```

5. Argo CD UI: `kubectl port-forward svc/argocd-server -n argocd 8080:443` → https://localhost:8080

The `spaceops-stage` Application syncs `values-stage-full.yaml` + GCP image parameters automatically
when `gcp.enabled: true`. Image tag promotion = commit to `values-gitops-stage.yaml`.

**Migrating from imperative Helm:** uninstall Helm release *or* let Argo adopt (advanced); simplest lab
path: `helm uninstall spaceops -n spaceops-stage` (keep namespace + secrets), then sync Argo Application.

Full runbook: [gitops_bootstrap.md](gitops_bootstrap.md) · [ADR 0008](../adr/0008-gitops-argocd.md)

---

## 7. Demo scenarios A/B (automated E2E)

```powershell
$env:GCP_PROJECT_ID = "spaceops-project"   # optional if LB IP already assigned
make gcp-stage-demo
# Scenario A only: make gcp-stage-demo GCP_STAGE_ARGS=--scenario a
```

Script flow: `GET /health` → ingest fixture → wait for persister → `POST /runs` scenarios A & B.

**Live observability during demo:**

```powershell
kubectl logs -n spaceops-stage -l app.kubernetes.io/component=api -f
kubectl port-forward -n spaceops-stage svc/spaceops-jaeger 16686:16686
```

**PR1.1 monitoring overlay:** create the Grafana admin Secret, then add
`-f deploy/helm/spaceops/values-monitoring-stage.yaml` to the Helm command in section 4.

```bash
kubectl create secret generic spaceops-stage-monitoring-secrets \
  -n spaceops-stage \
  --from-literal=grafana-admin-password='REPLACE_ME'
kubectl port-forward -n spaceops-stage svc/spaceops-prometheus 9090:9090
kubectl port-forward -n spaceops-stage svc/spaceops-grafana 3000:3000
```

Prometheus targets expected after the overlay: `spaceops-api`, `spaceops-nats`,
`spaceops-postgres`, and `spaceops-otel-collector`. Variant A `agent-worker` does not expose a
standalone metrics port yet; use API run metrics, queue/DLQ metrics, and traces for worker
operations until PR1.4 or a later worker metrics endpoint closes that gap.

**Scrape smoke (PR1.1):** with `kubectl port-forward ... svc/spaceops-prometheus 9090:9090` running:

```bash
curl -s http://127.0.0.1:9090/api/v1/targets \
  | jq -r '.data.activeTargets[] | select(.health=="up") | .labels.job' | sort -u
# Expected jobs: spaceops-api spaceops-nats spaceops-otel-collector spaceops-postgres
```

Without `jq`, open `http://127.0.0.1:9090/targets` and confirm the four jobs above are **UP**.

**SLO/alert smoke (PR1.2):**

```bash
curl -s http://127.0.0.1:9090/api/v1/rules
curl -s http://127.0.0.1:9090/api/v1/alerts
```

Confirm the `spaceops.slo.rules` group exists with `SpaceOpsApiDown`,
`SpaceOpsHighRunErrorRate`, `SpaceOpsEvidencePolicyViolations`, and
`SpaceOpsSyntheticPr12Probe`. The synthetic rule is inert (`vector(0)`) by default; see
[slo-production-readiness.md](../slo-production-readiness.md) for the temporary `vector(1)` drill.

**OTLP TLS (`tlsMode: mesh-sidecar`):** the OTel collector overlay sets `sidecar.istio.io/inject:
"true"`. Transparent mTLS applies only when a service mesh (e.g. Istio) is installed on the cluster.
Without mesh, in-cluster OTLP stays plaintext as in the PS6/PS7 lab baseline — not a regression for
ephemeral stage.

Manual curls: [portfolio README](../portfolio/README.md) (use `:8000` on LoadBalancer IP).

Checkpoint proof (`api.checkpoint.enabled: true`): [graph_worker_checkpoint_ops.md](graph_worker_checkpoint_ops.md).

---

## 8. Cost and shutdown

See cost table in [infra/terraform/gcp/README.md](../../infra/terraform/gcp/README.md).
The canonical policy is [stage_operating_policy.md](stage_operating_policy.md): ephemeral by
default, time-boxed long-lived stage only with owner, end time, budget alert, and daily drift check.

**Full teardown (trial end):** [gcp_stage_teardown.md](gcp_stage_teardown.md) — `make gcp-stage-down`

| Action | When |
|--------|------|
| `make gcp-stage-down` | One-command teardown: Helm + namespaces + Terraform destroy |
| `make gcp-stage-destroy GCP_STAGE_ARGS="--confirm"` | Tear down Helm + Terraform when trial ends |
| `terraform destroy` | Same (manual) |
| Preemptible nodes | Default in Terraform (`preemptible_nodes = true`) |
| Budget alerts | **PS6.9** — [cloud_cost_hygiene.md](cloud_cost_hygiene.md) + Terraform `budget.tf` |
| Scale-down overnight | **PS6.9** — `scripts/cloud/schedule_scale_down.sh` |

**Infra $ vs model $:** cluster cost is independent of [LLM token budget](gpu_cost_hygiene.md)
(PS5.6 process mode).

---

## 9. Cloud Run fallback (showcase only)

For a **serverless portfolio slice** without in-cluster Postgres/NATS:

- Container: same `spaceops-api` image from Artifact Registry
- Data: Cloud SQL + Memorystore or managed equivalents (Phase 7)
- **Not** PS6.8 default — documented so Phase 7 can demo “portable app, alternate runtime”

---

## 10. Destroy and recreate (stretch acceptance)

Target: one engineer can destroy and recreate stage in **<= 75 minutes** excluding manual population
of new real secrets. See [stage_operating_policy.md](stage_operating_policy.md) for the RTO budget
and drift-check drill.

```bash
helm uninstall spaceops -n spaceops-stage
kubectl delete namespace spaceops-stage --ignore-not-found
cd infra/terraform/gcp && terraform destroy
# Re-run sections 1–4
```

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `kubectl` OpenAPI validation fails against old endpoint | Run `gcloud container clusters list`; if `spaceops-stage` is absent, recreate/import the cluster before deploy |
| `gcloud get-credentials` returns 404 | Wrong project/region/name or deleted cluster; verify `GCP_PROJECT_ID`, `GCP_REGION`, `GKE_CLUSTER_NAME`, then run Terraform |
| `ImagePullBackOff` | Node SA has `artifactregistry.reader`; image path matches AR repo |
| API `Pending` | Node pool capacity; `kubectl describe pod` |
| Postgres `CrashLoopBackOff` / `lost+found` | Ensure chart has `postgres.dataDir` (pgdata subdir); upgrade Helm |
| ESO sync failed | WI annotation on ESO SA; GSM secret names match `remoteRefs` |
| LB IP pending | Wait 2–5 min; quota for external IPs in project |
| `curl` to `/health` fails | Use port **8000**, not 80 |
| Helm namespace ownership error | `--set global.createNamespace=false` if namespace created manually |
| Scenario A always `no_evidence` | Rebuild/push images after PS7.1 (telemetry NDJSON in image); run `make gcp-stage-deploy` (runs `index_kb`); confirm ingest + 20s persister wait |
| `SSD_TOTAL_GB` quota exceeded | Set `node_locations = ["us-central1-a"]`, `node_disk_size_gb = 30`, `node_disk_type = "pd-standard"` in `terraform.tfvars` |
| Terraform wants to **replace** healthy cluster | If cluster is healthy: `terraform untaint google_container_cluster.primary` then `apply`; do not auto-destroy |
| Failed apply left cluster **tainted** | `terraform state list`; fix root cause; untaint or `terraform destroy` and recreate (~45 min) |

See also [infra/terraform/gcp/README.md](../../infra/terraform/gcp/README.md) (PS7.1 live GCP lessons).

---

## Cross-links

- [Environment promotion](environment_promotion.md)
- [K8s rollout / rollback](k8s_rollout_rollback.md)
- [PS6.9 billing and shutdown controls](../../roadmap/02-production-scale/sprint-6/PS6.9-billing-shutdown-controls.md)
- [Cloud cost hygiene](cloud_cost_hygiene.md)
