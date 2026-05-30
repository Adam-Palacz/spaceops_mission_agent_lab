# PS6.2 — Deployment packaging (Helm)

| Field | Value |
|-------|-------|
| **Task ID** | PS6.2 |
| **Status** | Done |

---

## Description

Package SpaceOps for Kubernetes with **Helm** (default recommendation) and **values layering** for
`dev` / `stage` / `prod`. Close tool choice in the first ADR commit; do not maintain Helm + kustomize in parallel.

**Profiles:** ship a **minimal dev** chart subset first (see sprint README), then optional subcharts/profiles
for full compose parity (kb-mcp, jaeger, nats, NIM).

---

## Requirements

- [x] **Minimal dev profile (required):** `api`, `postgres`, `opa`, `telemetry-mcp` (or mock), `telemetry-persister` worker.
- [x] **Optional profiles:** kb-mcp, remaining MCPs, `otel-collector`, `jaeger`, `nats`, NIM/GPU — toggled via values.
- [x] **Agent graph worker** manifest stub (`agentWorker.enabled`, default false — Variant B api path).
- [x] Values files: `values-dev.yaml`, `values-stage.yaml`, `values-prod.yaml` (+ `values-minimal-dev.yaml`).
- [x] **LLM env wiring:** `LLM_BACKEND`, budget vars, GPU URLs — from PS6.1 matrix; secrets via PS6.6 refs pattern.
- [x] **PS5.7 mount:** API `/app/var` via emptyDir or `existingClaim` in values.
- [x] Optional **NIM** profile: **off** by default; node selector / tolerations documented in values.
- [x] Image tags pinned in values; align with `docker compose` build targets.
- [x] Liveness/readiness probes for api and worker; NIM health path `/v1/health/ready`.

---

## Dependencies

- **PS6.1** — env matrix and promotion rules.
- **PS5.3–PS5.4** — GPU adapter and health semantics.
- **PS3.9** — api checkpoint env vars per PS6.11 fork.

---

## Checklist

- [x] ADR: [0006-kubernetes-packaging-helm.md](../../../docs/adr/0006-kubernetes-packaging-helm.md)
- [x] `helm template` succeeds in CI (`k8s-manifest-lint.yml`)
- [x] Compose → K8s mapping in [deploy/helm/spaceops/README.md](../../../deploy/helm/spaceops/README.md)
- [x] Resource requests/limits baseline per service in values

---

## Test / acceptance

- [x] Render manifests for all three env overlays without error (CI + `tests/test_helm_ps62.py`)
- [x] Deploy on local cluster (PS6.3) using packaged manifests.
- [x] Changing `LLM_BACKEND` in values and redeploying does not require image rebuild

---

## Deliverables

- [deploy/helm/spaceops/](../../../deploy/helm/spaceops/)
- [.github/workflows/k8s-manifest-lint.yml](../../../.github/workflows/k8s-manifest-lint.yml)
- `make helm-template` / `make helm-lint`

---

## Out of scope

- Multi-cluster federation.
- Cloud-specific ingress controllers (document port-forward for local).
