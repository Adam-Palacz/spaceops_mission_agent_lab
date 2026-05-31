# Runbook — GCP stage deploy (PS6.8)

Deploy SpaceOps to a **small GKE stage cluster** using the same Helm chart and `values-stage.yaml`
overlays as local kind. This is the **stretch** acceptance path; minimum PS6.8 DoD is Terraform
validate + documentation only.

**Related:** [ADR 0009](../adr/0009-gcp-baseline-portable-first.md),
[infra/terraform/gcp/README.md](../../infra/terraform/gcp/README.md),
[PS6.9 billing controls](../../roadmap/02-production-scale/sprint-6/PS6.9-billing-shutdown-controls.md)

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

## 1. Provision infrastructure

```bash
cd infra/terraform/gcp
cp terraform.tfvars.example terraform.tfvars   # set project_id
terraform init
terraform plan
terraform apply
```

Save outputs:

```bash
terraform output -json > /tmp/spaceops-gcp-outputs.json
eval "$(terraform output -raw get_credentials_command)"
terraform output artifact_registry_repository
terraform output eso_service_account_email
```

**Validate-only (no GCP):** `make terraform-gcp-validate`

---

## 2. Build and push images (Artifact Registry)

Set variables from Terraform outputs:

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

Same chart as PS6.2 / PS6.3; stage overlay + GCP image hosts:

```bash
export NAMESPACE=spaceops-stage
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install spaceops deploy/helm/spaceops \
  --namespace "${NAMESPACE}" \
  -f deploy/helm/spaceops/values.yaml \
  -f deploy/helm/spaceops/values-stage.yaml \
  -f deploy/helm/spaceops/values-gcp-stage.yaml \
  --set images.api.repository="${AR_REPO}/api" \
  --set images.mcp.repository="${AR_REPO}/mcp" \
  --set images.api.tag="${TAG}" \
  --set images.mcp.tag="${TAG}" \
  --wait --timeout 10m
```

Verify:

```bash
kubectl get pods,svc -n "${NAMESPACE}"
kubectl get svc spaceops-api -n "${NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
curl -s "http://$(kubectl get svc spaceops-api -n "${NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')/health"
```

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

After cluster bootstrap, install Argo CD per [gitops_bootstrap.md](gitops_bootstrap.md). Point
`spaceops-stage` Application at this cluster context; use `values-gitops-stage.yaml` for image tag
pins.

---

## 7. Demo scenarios A/B (stretch)

With observability enabled in `values-stage.yaml`:

1. Run scenario A/B via API (same as local `make k8s-smoke` / rollout docs).
2. Confirm traces in Jaeger (port-forward or internal LB if added).
3. Checkpoint proof: `api.checkpoint.enabled: true` — verify resume path per ADR 0005.

---

## 8. Cost and shutdown

See cost table in [infra/terraform/gcp/README.md](../../infra/terraform/gcp/README.md).

| Action | When |
|--------|------|
| `terraform destroy` | Tear down lab cluster when done |
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

Target: one engineer can destroy and recreate stage in ~45 minutes (excluding secret population).

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
| `ImagePullBackOff` | Node SA has `artifactregistry.reader`; image path matches AR repo |
| API `Pending` | Node pool capacity; `kubectl describe pod` |
| ESO sync failed | WI annotation on ESO SA; GSM secret names match `remoteRefs` |
| LB IP pending | Wait 2–5 min; quota for external IPs in project |

---

## Cross-links

- [Environment promotion](environment_promotion.md)
- [K8s rollout / rollback](k8s_rollout_rollback.md)
- [PS6.9 billing and shutdown controls](../../roadmap/02-production-scale/sprint-6/PS6.9-billing-shutdown-controls.md)
- [Cloud cost hygiene](cloud_cost_hygiene.md)
