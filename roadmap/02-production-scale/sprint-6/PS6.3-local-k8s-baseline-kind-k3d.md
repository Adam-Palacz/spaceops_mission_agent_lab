# PS6.3 — Local K8s baseline (kind / k3d)

| Field | Value |
|-------|-------|
| **Task ID** | PS6.3 |
| **Status** | Todo |

---

## Description

Prove the stack runs on a **local Kubernetes cluster** (kind or k3d) using the same packaging as
stage/prod (PS6.2). Operator entrypoint: **`make k8s-up`** / **`make k8s-down`**.

---

## Requirements

- [ ] Choose default local tool: **kind** or **k3d** (document why; single default in Makefile).
- [ ] One-command cluster create + deploy **minimal dev profile** from PS6.2 Helm chart.
- [ ] **Required** in minimal profile: **api**, **postgres**, **opa**, **telemetry-mcp** (or slim mock),
      **telemetry-persister** worker. OPA is not optional — safe baseline includes fail-closed policy path.
- [ ] **Optional** via Helm values (off by default locally): kb-mcp, full MCP set, otel-collector, jaeger,
      nats, NIM/GPU profile.
- [ ] **Windows dev:** document kind/k3d on native Docker vs WSL2; test `make k8s-up` from PowerShell
      and WSL; note path/line-ending pitfalls for mounted volumes.
- [ ] Observability: OTel + Jaeger **optional profile**; port-forward documented when enabled.
- [ ] **No GPU node** in default local cluster; NIM remains compose/profile or optional manifest
      toggle off by default.
- [ ] Document resource minimums (CPU/RAM) for laptop dev.

---

## Dependencies

- **PS6.1** — namespace names and env overlay selection.
- **PS6.2** — deploy manifests exist before `k8s-up` can succeed.

---

## Checklist

- [ ] `infra/k8s/` or `deploy/` local bootstrap scripts.
- [ ] Makefile targets: `k8s-up`, `k8s-down`, `k8s-status` (or documented equivalents).
- [ ] Runbook: install prerequisites (Docker, kind/k3d, kubectl, helm).
- [ ] Smoke: `GET /health` on API via port-forward after `make k8s-up`.

---

## Test / acceptance

- [ ] Fresh machine path: clone → `make k8s-up` → API health 200 (documented timeouts).
- [ ] `make k8s-down` leaves no orphaned kind/k3d cluster (or documents cleanup).
- [ ] CI does **not** require local K8s on every PR (optional workflow_dispatch job acceptable).

---

## Deliverables (expected)

- `infra/k8s/local/` (cluster config + README)
- Makefile targets
- `docs/runbooks/local_k8s_dev.md`

---

## Out of scope

- Production GKE cluster (PS6.8).
- Full UI profile in cluster (optional toggle).
