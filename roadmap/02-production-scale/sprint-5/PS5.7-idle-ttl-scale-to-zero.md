# PS5.7 — Idle TTL and scale-to-zero workflow

| Field | Value |
|-------|-------|
| **Task ID** | PS5.7 |
| **Status** | Done |

---

## Description

GPU (NIM) should **not** run 24/7 in a lab repo. Provide **host-run** operator scripts for
stop-by-default, idle shutdown after TTL, and explicit `make gpu-up` / `make gpu-down`.

**Security boundary (fixed for sprint):** shutdown scripts run on the **host** invoking
`docker compose stop` (or equivalent). **No** sidecar with Docker socket in the compose stack.

---

## Activity signal (required — not optional)

Gateway **must** update a durable **`last_gpu_call_at`** on every successful call where
`backend_actual=gpu` (ISO-8601 UTC).

### Host ↔ API visibility (required — PS5.3 + PS5.7)

When the API/agent runs **inside Compose** (typical `make gpu-up`), the activity file must live on a
**host-visible path**, not only inside an ephemeral container filesystem.

| Layer | Path | Notes |
|-------|------|-------|
| **Host** | `./var/llm_last_gpu_call_at` | Read by `gpu_idle_shutdown.sh` / `.ps1` |
| **Container (API)** | `/app/var/llm_last_gpu_call_at` | Written by gateway |
| **Compose** | bind mount **`./var:/app/var`** on `api` (and worker if it calls LLM) | Required in `gpu` profile |

Env override: `GPU_ACTIVITY_FILE` — if set, must still resolve to the **same** path on host and in
container (document relative-to-repo-root convention).

Idle shutdown scripts read **`./var/llm_last_gpu_call_at` from the repo root** (cwd = repo root in
`make gpu-idle-check`). If missing and NIM is up → treat as idle since container start minus grace
(documented in runbook).

PS5.7 is **not** Done without: (1) compose mount in PS5.3, (2) gateway write, (3) host script read
after a request through the **containerized** API.

---

## Requirements

- [x] Default: no `gpu` profile on plain `docker compose up`.
- [x] `GPU_IDLE_TTL_MINUTES` (default 45): host script stops NIM service after idle period.
- [x] `make gpu-up` / `make gpu-down` idempotent (bash + PowerShell documented).
- [x] Scripts: `scripts/gpu_idle_shutdown.sh` and `scripts/gpu_idle_shutdown.ps1` with **`--dry-run`**.
- [x] Dry-run prints: last activity timestamp, TTL, would-stop yes/no — **no** container stop.
- [x] After real stop, next `LLM_BACKEND=gpu` call → PS5.4 fallback or explicit error (documented).

---

## Dependencies

- **PS5.3** — NIM compose profile.
- **PS5.1** — `backend_actual` metadata for activity signal.

---

## Checklist

- [x] Gateway writes `last_gpu_call_at` on `backend_actual=gpu`.
- [x] `.gitignore` includes `var/llm_last_gpu_call_at` (or chosen path).
- [x] Runbook: demo day vs overnight — `make gpu-down` or idle script.
- [x] CI does not start GPU (comment in `ci.yml`).

---

## Test / acceptance

- [x] Automated: dry-run bash script exits 0 with fixture timestamp (no docker required).
- [x] Automated: dry-run PowerShell script same scenario.
- [x] **Integration (required):** with `api` up under `gpu` profile and `./var:/app/var` mounted —
      one LLM call via containerized API (e.g. `POST /runs` or `scripts/llm_gpu_smoke` against API) →
      host reads `./var/llm_last_gpu_call_at` with fresh timestamp → `gpu_idle_shutdown.* --dry-run`
      reports would-not-stop. Operator command: `make gpu-idle-integration`.
- [x] Manual: stale timestamp → dry-run → would-stop; then real run stops NIM (record in PR).

---

## Deliverables (expected)

- `scripts/gpu_idle_shutdown.sh` — `--dry-run`
- `scripts/gpu_idle_shutdown.ps1` — `-DryRun`
- `Makefile` — `gpu-idle-check` (dry-run wrapper)
- `docs/runbooks/gpu_cost_hygiene.md`

---

## Out of scope

- In-cluster sidecar with Docker socket (PS6+ if ever needed).
