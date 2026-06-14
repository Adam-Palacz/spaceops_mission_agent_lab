# PS7.1 — Live stage GKE deploy

| Field | Value |
|-------|--------|
| **Task ID** | PS7.1 |
| **Status** | Done |
| **Source** | PS6.8 stretch; [gcp_stage_deploy.md](../../../docs/runbooks/gcp_stage_deploy.md) |

## Description

Reproducible deploy of SpaceOps to **stage GKE** with Terraform + Helm (`values-gcp-stage.yaml`).
Proof: demo scenarios A/B with trace and evidence in cloud.

## Requirements

- [x] `terraform apply` on stage project (documented vars) and non-empty Terraform state.
- [x] Stage variables use a small quota-safe node shape (`node_locations`, disk size/type) and avoid surprise regional 3x100GB defaults.
- [x] Artifact Registry repository exists before `make gcp-stage-images`.
- [x] Helm install with secrets via ESO/SOPS path (no plain-text in Git); lab may use `k8s_secrets_bootstrap` + K8s Secret.
- [x] Ingress/LB for API; UI optional.
- [x] Runbook: destroy/recreate time-boxed.

## Acceptance

- [x] Operator completes runbook flow without ad-hoc steps (`terraform apply` → `make gcp-stage-images` → `make gcp-stage-deploy` → `make gcp-stage-demo`).
- [x] Scenarios A and B from `docs/portfolio/README.md` pass on stage (`scripts/gcp_stage.py demo` validates).
- [x] `terraform plan` does not propose replacing a healthy cluster unless the operator intentionally taints/destroys it (documented untaint path).
- [x] GCP troubleshooting notes cover SSD quota exhaustion, failed cluster operations, and safe recovery (`terraform untaint` / recreate decision).

## Live GCP lessons to capture

- Regional GKE can multiply node disk usage across zones; pin `node_locations` for the lab stage cluster.
- Keep node disk size/type explicit in Terraform to avoid quota failures on small projects.
- Treat a tainted but healthy cluster as a recovery decision, not an automatic destroy/recreate path.
- **Artifact Registry:** `make gcp-stage-images` must run after Terraform creates the AR repo; otherwise Docker push fails with `Repository "spaceops" not found`.
- **Empty Terraform state:** if the GKE cluster exists but `terraform state list` is empty, do not run a blind full apply. Reconcile/import existing resources or target only missing prerequisites first.
- **Stale kubeconfig:** if `kubectl` tries an old endpoint but `gcloud container clusters list` shows no `spaceops-stage`, the cluster is gone. Recreate/import it before secrets or Helm.
- **MCP telemetry on GKE:** root `.dockerignore` must allow `data/telemetry/` in api/mcp images; otherwise scenario A gets `no_evidence`.
- **KB on GKE:** `make gcp-stage-deploy` runs `index_kb` in the kb-mcp pod after migrations (full stack).
- **One-command lifecycle:** `make gcp-stage-up` wraps Terraform apply, image push, deploy, smoke, and demo; `make gcp-stage-down` wraps confirmed Helm + Terraform teardown.

## Completion evidence (2026-06-03)

- Project: `spaceops-project-498213`
- Cluster: `spaceops-stage` in `us-central1`, one Terraform-managed node pool.
- Artifact Registry: `us-central1-docker.pkg.dev/spaceops-project-498213/spaceops`
- API LoadBalancer: `http://35.192.87.194:8000/health`
- `make gcp-stage-deploy`: Helm release `spaceops` deployed, migrations ran, KB index command executed.
- `make gcp-stage-smoke`: `{'status': 'ok', 'service': 'spaceops-api'}`
- `make gcp-stage-demo GCP_STAGE_ARGS="--scenario both"`:
  - Scenario A run: `3399849bb98a4c99bbfa2be6f64ac0d0`, trace `6f0a67af4941f4d282287651039cac86`, PASS with evidence.
  - Scenario B run: `a2221710faaa4ccf9c76e17bc05d27d1`, trace `1c444053d6db4f9700c6df5a6e415280`, PASS with `no_evidence` escalation.
- `make gcp-stage-down`: Helm release/namespace removed and Terraform destroyed 19 resources; post-checks found no GKE clusters, no Artifact Registry repos, and empty Terraform state.

## Infra shutdown (trial end)

GCP free trial on the original account ended; stage infra should be removed before opening a
**new** project on a separate Google account.

```powershell
$env:GCP_PROJECT_ID = "spaceops-project-498213"
make gcp-stage-down
```

Runbook: [gcp_stage_teardown.md](../../../docs/runbooks/gcp_stage_teardown.md).

**Resume PS7.1 later:** new project → `terraform.tfvars` → `$env:GCP_PROJECT_ID=...`
→ `make gcp-stage-up`.
Use `make gcp-terraform-ar` only as targeted recovery for a missing Artifact Registry repo,
not as the normal stage bring-up.

---

## Current failure recovery

For `make gcp-stage-images` failing with `Repository "spaceops" not found`:

```powershell
cd infra/terraform/gcp
terraform state list
terraform output artifact_registry_repository
gcloud artifacts repositories list --project=spaceops-project --location=us-central1
```

If state is empty and the cluster already exists, create only the missing Artifact Registry prerequisite
through Terraform before pushing images:

```powershell
# or from repo root:
make gcp-terraform-ar

# manual equivalent:
terraform apply `
  -target=google_project_service.apis `
  -target=google_artifact_registry_repository.spaceops `
  -target=google_project_iam_member.gke_nodes_ar_reader
```

Then re-run:

```powershell
cd ../../..
$env:GCP_PROJECT_ID = "spaceops-project"
make gcp-stage-images
```

For `make gcp-stage-deploy` failing while `kubectl` validates against an old API endpoint:

```powershell
gcloud container clusters list --project=spaceops-project --region=us-central1
kubectl config current-context
kubectl config get-contexts
```

If the cluster list is empty, stop the deploy and recreate/import the cluster with Terraform before
running `make gcp-kube-credentials` or `make gcp-stage-deploy`.

## Operator quick path (2026-05-31)

```powershell
. .\scripts\refresh_dev_path.ps1
$env:GCP_PROJECT_ID = "spaceops-project-498213"
$env:GCP_IMAGE_TAG = "stage"
make gcp-stage-up
```

**Evidence:** LoadBalancer API (e.g. `http://<EXTERNAL-IP>:8000/health`), `gcp-stage-demo` scenario validators, Jaeger via `kubectl port-forward svc/spaceops-jaeger -n spaceops-stage 16686:16686`.

## Implementation notes (repo)

| Artifact | Purpose |
|----------|---------|
| `.dockerignore` | Include `data/telemetry/` in AR images |
| `scripts/gcp_stage.py` | deploy / smoke / demo + portfolio validators + `index_kb` |
| `scripts/gcp_stage_images.py` | `make gcp-stage-images` |
| `values-gcp-stage.yaml` | LoadBalancer + `JAEGER_UI_URL` for port-forward |
| `docs/runbooks/gcp_stage_deploy.md` | Full runbook + PS7.1 troubleshooting |
