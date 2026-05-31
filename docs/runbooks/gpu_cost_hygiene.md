# GPU cost hygiene runbook (PS5.7)

Use this runbook to keep local GPU/NIM usage stop-by-default and avoid running NIM all day.

## Default operating mode

- Start GPU runtime only when needed (`make gpu-up`).
- Stop explicitly after work (`make gpu-down`).
- Use idle TTL checks for unattended sessions.

## Activity signal contract

- Gateway writes successful GPU activity timestamp to:
  - host: `./var/llm_last_gpu_call_at`
  - API container: `/app/var/llm_last_gpu_call_at`
- Compose must bind mount `./var:/app/var` so host scripts see container updates.

## Idle check commands

### Bash / POSIX

```bash
scripts/gpu_idle_shutdown.sh --dry-run
```

### PowerShell

```powershell
.\scripts\gpu_idle_shutdown.ps1 -DryRun
```

### Make wrapper

```bash
make gpu-idle-check
```

### API integration acceptance

Run the PS5.7 end-to-end acceptance only on a machine configured for NIM/GPU:

```bash
make gpu-idle-integration
```

This starts `nim-llm` and `api` with the `gpu` profile, calls `POST /runs`, verifies that
`./var/llm_last_gpu_call_at` was freshly written through the `./var:/app/var` bind mount, then runs
the host idle dry-run and expects `would_stop=false`.

Dry-run output includes:

- `last_activity_utc`
- `idle_minutes`
- `ttl_minutes`
- `would_stop=true|false`

## Real stop

When dry-run reports `would_stop=true`, run without dry-run:

```bash
scripts/gpu_idle_shutdown.sh
```

or:

```powershell
.\scripts\gpu_idle_shutdown.ps1
```

## Tunables

- `GPU_IDLE_TTL_MINUTES` (default `45`)
- `GPU_ACTIVITY_FILE` (default host path `./var/llm_last_gpu_call_at`)

## If activity file is missing

If NIM is running and activity file is missing/invalid, scripts treat the service as idle and report `would_stop=true` (fail-safe for cost hygiene).

## After stop behavior

After NIM is stopped:

- `LLM_BACKEND=gpu` calls will either fallback via PS5.4 (if OpenAI available) or fail with explicit provider error.

## Cloud infra cost (PS6.9)

Host idle TTL (this runbook) covers **local compose/NIM**. **GKE stage/prod** billing, budget alerts,
and overnight node-pool scale-down are in [cloud_cost_hygiene.md](cloud_cost_hygiene.md). **No GPU node
pool on GKE by default** — Phase 7 only.
