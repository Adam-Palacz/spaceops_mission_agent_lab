# PS6.3 — Deployment packaging (Helm)

| Field | Value |
|-------|-------|
| **Task ID** | PS6.3 |
| **Status** | Todo |

---

## Description

Package SpaceOps for Kubernetes with **Helm** (default recommendation) and **values layering** for
`dev` / `stage` / `prod`. Close tool choice in the first ADR commit; do not maintain Helm + kustomize in parallel.

**Profiles:** ship a **minimal dev** chart subset first (see sprint README), then optional subcharts/profiles
for full compose parity (kb-mcp, jaeger, nats, NIM).

---

## Requirements

- [ ] **Minimal dev profile (required):** `api`, `postgres`, `opa`, `telemetry-mcp` (or mock), `telemetry-persister` worker.
- [ ] **Optional profiles:** kb-mcp, remaining MCPs, `otel-collector`, `jaeger`, `nats`, NIM/GPU — toggled via values.
- [ ] **Agent graph worker** manifest stub only until PS6.1 fork ADR selects variant A; variant B uses api Deployment only.
- [ ] Values files: `values-dev.yaml`, `values-stage.yaml`, `values-prod.yaml` (+ `values-minimal-dev.yaml`).
- [ ] **LLM env wiring:** `LLM_BACKEND`, budget vars, GPU URLs — from PS6.1 matrix; secrets via
      PS6.6 refs only.
- [ ] **PS5.7 mount:** `./var` equivalent for API — `PersistentVolumeClaim` or documented emptyDir
      + sidecar pattern for `llm_last_gpu_call_at` when GPU profile enabled in cluster.
- [ ] Optional **NIM** subchart/profile: **off** by default; node selector / tolerations for GPU nodes
      documented (Phase 7 prep).
- [ ] Image tags pinned; align with `docker compose` build targets (PS4 docker-build parity).
- [ ] Liveness/readiness probes for api and worker; NIM health path matches PS5.4.

---

## Dependencies

- **PS6.1** — env matrix and promotion rules.
- **PS5.3–PS5.4** — GPU adapter and health semantics.
- **PS3.9** — api/worker deploy must support checkpoint env vars per PS6.11 fork.

---

## Checklist

- [ ] ADR: confirm **Helm** (expected) and directory layout under `deploy/helm/spaceops/`.
- [ ] `helm template` succeeds in CI (`compose-config`-style job).
- [ ] Document which compose services map to which K8s workloads.
- [ ] Resource requests/limits baseline per service.

---

## Test / acceptance

- [ ] Render manifests for all three env overlays without error.
- [ ] Deploy on local cluster (PS6.2) using packaged manifests.
- [ ] Changing `LLM_BACKEND` in values and redeploying does not require image rebuild.

---

## Deliverables (expected)

- `deploy/helm/spaceops/` (with `values-minimal-dev.yaml` + env overlays)
- `values-*.yaml` env overlays
- `.github/workflows/k8s-manifest-lint.yml` (optional, lightweight)

---

## Out of scope

- Multi-cluster federation.
- Cloud-specific ingress controllers (document port-forward for local).
