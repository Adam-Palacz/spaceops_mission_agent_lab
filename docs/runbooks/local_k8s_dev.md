# Local Kubernetes development (PS6.3)

Run SpaceOps on a **local kind cluster** using the same Helm chart as stage/prod ([PS6.2](../../deploy/helm/spaceops/README.md)).

## Default tool: kind

We standardize on **[kind](https://kind.sigs.k8s.io/)** (not k3d) because:

- CNCF-aligned, widely documented with Helm tutorials
- Works with Docker Desktop on Windows, macOS, and Linux
- Simple single-node config for laptop dev (`infra/k8s/local/kind-config.yaml`)

k3d remains a valid alternative; this repo does not automate it.

## Prerequisites

| Tool | Purpose |
|------|---------|
| **Docker** | Build images + kind node provider |
| **kind** | Local cluster |
| **kubectl** | Cluster admin |
| **helm** | Install PS6.2 chart |

Install examples:

- kind: `go install sigs.k8s.io/kind@v0.27.0` or package manager / [releases](https://github.com/kubernetes-sigs/kind/releases)
- helm: [Helm install docs](https://helm.sh/docs/intro/install/)

**Resource minimums (laptop):** 4 CPU / 8 GiB RAM recommended for minimal profile (api, postgres, opa, telemetry-mcp, nats, persister). Close GPU/NIM profiles unless needed.

## Quick start

From repo root:

```powershell
# PowerShell: refresh PATH after winget installs (stale terminal fix)
. .\scripts\refresh_dev_path.ps1
```

```bash
make k8s-down
make k8s-up          # new clusters: Calico CNI for NetworkPolicy enforcement (PS6.5)
make k8s-status
make k8s-smoke       # GET /health via port-forward
make k8s-isolation-verify
make k8s-down
```

**Migrating** from an older kindnet-only cluster: run `make k8s-down` then `make k8s-up` once.
Skip Calico for faster bootstrap (no cross-namespace proof): `K8S_SKIP_CALICO=1 make k8s-up`.

`k8s-up` will:

1. `docker compose build api telemetry-mcp`
2. Tag images as `spaceops-api:local` / `spaceops-mcp:local`
3. Create kind cluster `spaceops-dev` (if missing)
4. `kind load docker-image …`
5. `helm upgrade --install` with `values-dev.yaml` + `values-minimal-dev.yaml`
6. Wait for API deployment + smoke `/health`

**Timeouts:** first run may take **5–15 minutes** (image build + postgres PVC bind + pulls for postgres/opa/nats).

### Port-forward (manual)

```bash
kubectl port-forward -n spaceops-dev svc/spaceops-api 8000:8000
curl http://127.0.0.1:8000/health
```

### Optional observability

Enable in Helm values (not default locally):

```yaml
observability:
  otelCollector:
    enabled: true
  jaeger:
    enabled: true
```

Then port-forward Jaeger UI: `kubectl port-forward -n spaceops-dev svc/spaceops-jaeger 16686:16686`

## Windows notes

| Environment | Guidance |
|-------------|----------|
| **Docker Desktop (WSL2 backend)** | Recommended. Run `make k8s-up` from **WSL2** or **Git Bash**; ensure `kind`, `kubectl`, `helm` are on PATH inside that environment. |
| **PowerShell** | Run `. .\scripts\refresh_dev_path.ps1` after installing tools (winget does not update open terminals). Then `make k8s-up`. Prefer WSL2 if GNU make causes issues. |
| **Volume paths** | kind loads **container images**, not host bind mounts — avoids CRLF/path issues from compose `./data` mounts. API uses `emptyDir` in minimal profile. |

### kind missing

```powershell
# Option A: repo helper (direct download, no winget id guesswork)
powershell -ExecutionPolicy Bypass -File scripts/install_kind.ps1
powershell -ExecutionPolicy Bypass -File scripts/install_argocd_cli.ps1   # optional PS6.7 GitOps
. .\scripts\refresh_dev_path.ps1

# Option B: winget
winget install -e --id Kubernetes.kind
. .\scripts\refresh_dev_path.ps1
```

### `make` / `python` on Windows

- **GnuWin32 make** + `@echo.` breaks `make help` — fixed in Makefile (uses Python for blank lines).
- **Makefile** auto-uses `.venv\Scripts\python.exe` when present (no need to activate venv for `make k8s-up`).
- Disable **App execution alias** for `python.exe` in Windows Settings if `python` opens the Store stub.

```powershell
. .\scripts\refresh_dev_path.ps1   # refresh PATH + tool check
make k8s-up
```

Or without make:

```powershell
.venv\Scripts\python.exe scripts/k8s_local.py up
```

Set postgres password for local install (optional):

```powershell
$env:K8S_POSTGRES_PASSWORD = "spaceops"
make k8s-up
```

Skip rebuild when images already tagged:

```bash
K8S_SKIP_BUILD=1 make k8s-up
```

## Environment mapping

| Compose (dev) | kind + Helm |
|---------------|-------------|
| `docker compose up` | `make k8s-up` |
| `.env` secrets | Helm `secrets.create` + `K8S_POSTGRES_PASSWORD` (see [k8s_secrets_bootstrap.md](k8s_secrets_bootstrap.md)) |
| GPU / NIM profile | Stay on compose (`make gpu-up`) — **no GPU node** in default kind cluster |

See [environment_promotion.md](environment_promotion.md) for promotion to stage/prod.

## Database migrations

`/health` does not require migrations. For agent runs against cluster Postgres:

```bash
kubectl port-forward -n spaceops-dev svc/spaceops-postgres 5432:5432
# another shell:
DATABASE_URL=postgresql://spaceops:spaceops@localhost:5432/spaceops python -m alembic upgrade head
```

Match password to `K8S_POSTGRES_PASSWORD` / Helm `secrets.postgresPassword`.

## Troubleshooting

| Symptom | Action |
|---------|--------|
| `ImagePullBackOff` on api/mcp | Re-run `make k8s-up` (reloads local tags) or `kind load docker-image spaceops-api:local --name spaceops-dev` |
| Stale cluster | `make k8s-down` then `make k8s-up` |
| Helm stuck on postgres | `kubectl get pvc -n spaceops-dev`; ensure Docker disk space |
| Port-forward in use | Change `K8S_API_LOCAL_PORT` (default `18000` for smoke script) |

## Related

- [Helm chart README](../../deploy/helm/spaceops/README.md)
- [K8s rollout and rollback (PS6.4)](k8s_rollout_rollback.md)
- [K8s environment isolation (PS6.5)](k8s_environment_isolation.md)
- [ADR 0006 — Kubernetes packaging (Helm)](../adr/0006-kubernetes-packaging-helm.md)
- PS6.3 spec: `roadmap/02-production-scale/sprint-6/PS6.3-local-k8s-baseline-kind-k3d.md`
