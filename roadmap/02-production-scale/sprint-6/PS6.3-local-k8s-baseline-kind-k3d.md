# PS6.3 — Local K8s baseline (kind / k3d)

| Field | Value |
|-------|-------|
| **Task ID** | PS6.3 |
| **Status** | Done |

---

## Description

Prove the stack runs on a **local Kubernetes cluster** (kind or k3d) using the same packaging as
stage/prod (PS6.2). Operator entrypoint: **`make k8s-up`** / **`make k8s-down`**.

**Default tool:** **kind** (documented in runbook; k3d not automated).

---

## Requirements

- [x] Choose default local tool: **kind** (portable, Docker Desktop friendly; single default in Makefile).
- [x] One-command cluster create + deploy **minimal dev profile** from PS6.2 Helm chart.
- [x] **Required** in minimal profile: **api**, **postgres**, **opa**, **telemetry-mcp**, **telemetry-persister** (+ nats for persister).
- [x] **Optional** via Helm values (off by default locally): kb-mcp, full MCP set, otel-collector, jaeger, NIM/GPU profile.
- [x] **Windows dev:** documented in runbook (Docker Desktop WSL2 vs PowerShell, emptyDir vs compose mounts).
- [x] Observability: OTel + Jaeger optional; port-forward documented.
- [x] **No GPU node** in default local cluster; NIM off in values.
- [x] Document resource minimums (CPU/RAM) for laptop dev.

---

## Dependencies

- **PS6.1** — namespace names and env overlay selection.
- **PS6.2** — deploy manifests exist before `k8s-up` can succeed.

---

## Checklist

- [x] `infra/k8s/local/` (kind config + README)
- [x] Makefile targets: `k8s-up`, `k8s-down`, `k8s-status`, `k8s-smoke`
- [x] Runbook: [docs/runbooks/local_k8s_dev.md](../../../docs/runbooks/local_k8s_dev.md)
- [x] Smoke: `GET /health` via `make k8s-smoke` / built into `make k8s-up`

---

## Test / acceptance

- [x] Fresh machine path documented: clone → `make k8s-up` → API health 200 (timeouts documented).
- [x] `make k8s-down` deletes kind cluster `spaceops-dev` (or `--keep-cluster` for helm-only).
- [x] CI does **not** require local K8s on every PR (`workflow_dispatch` in `k8s-local-smoke.yml`).

---

## Deliverables

- [infra/k8s/local/](../../../infra/k8s/local/)
- [scripts/k8s_local.py](../../../scripts/k8s_local.py)
- [docs/runbooks/local_k8s_dev.md](../../../docs/runbooks/local_k8s_dev.md)
- [tests/test_k8s_ps63.py](../../../tests/test_k8s_ps63.py)
- [.github/workflows/k8s-local-smoke.yml](../../../.github/workflows/k8s-local-smoke.yml) (optional manual)

---

## Out of scope

- Production GKE cluster (PS6.8).
- Full UI profile in cluster (optional toggle).
