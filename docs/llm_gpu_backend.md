# GPU / NVIDIA NIM backend (PS5.3)

Optional **`LLM_BACKEND=gpu`** routes agent LLM calls to a local [**NVIDIA NIM**](https://docs.nvidia.com/nim/)
container (OpenAI-compatible API). Default stack uses **`LLM_BACKEND=openai`**; NIM is **off** unless
you enable the Compose **`gpu`** profile.

## Prerequisites

- NVIDIA GPU + [Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- [NGC API key](https://org.ngc.nvidia.com/setup/api-key) in `.env` as `NGC_API_KEY`
- Pull rights for `nvcr.io/nim/microsoft/phi-4-mini-instruct:1.12.0` (override with `NIM_IMAGE`)

## Configuration

| Env | Description |
|-----|-------------|
| `LLM_BACKEND` | Set to `gpu` when using NIM |
| `GPU_LLM_BASE_URL` | Host gateway/smoke URL, normally `http://localhost:8005` |
| `GPU_LLM_CONTAINER_BASE_URL` | Optional API-container override; defaults to `http://nim-llm:8000` in Compose |
| `GPU_LLM_MODEL_ID` | NIM model name; local default is `qwen/qwen2.5-0.5b-instruct` |
| `GPU_LLM_API_KEY` | Optional bearer (usually empty for local NIM) |
| `GPU_ACTIVITY_FILE` | Default resolves to `./var/llm_last_gpu_call_at` on host and `/app/var/llm_last_gpu_call_at` in API container |
| `NGC_API_KEY` | Required for NIM container image pull/runtime |
| `NIM_IMAGE` | Local default: `nvcr.io/nim/microsoft/phi-4-mini-instruct:1.12.0` |
| `NIM_RELAX_MEM_CONSTRAINTS` | Local default `1`; bypasses NIM's 95% free-memory admission check |
| `NIM_NUM_KV_CACHE_SEQ_LENS` | Local default `1`; minimizes KV cache allocation with relaxed checks |
| `NIM_MODEL_PROFILE` | Local default `default`; runtime selects a compatible generic profile on the tested RTX GPU |
| `NIM_MODEL_NAME` | Checkpoint source, default `hf://Qwen/Qwen2.5-0.5B-Instruct` |
| `NIM_SERVED_MODEL_NAME` | API model name, default `qwen/qwen2.5-0.5b-instruct` |

## Operator workflow

```bash
# The runtime uses a small Qwen 0.5B checkpoint and constrained-memory
# settings for local 8 GB validation.

# From repo root — starts NIM, waits for /v1/health/ready
make gpu-up

# Health only
python scripts/llm_gpu_smoke.py --health-only

# Host-side generate (set LLM_BACKEND=gpu and GPU_LLM_BASE_URL=http://localhost:8005 in .env)
# Leave GPU_LLM_CONTAINER_BASE_URL unset unless overriding the API-to-NIM route.
python scripts/llm_gpu_smoke.py --generate

# Stop NIM
make gpu-down
```

Windows PowerShell equivalent when GNU Make is not installed:

```powershell
docker compose -f infra/docker-compose.yml --project-directory . --profile gpu up -d nim-llm
.\.venv\Scripts\python.exe scripts\llm_gpu_smoke.py --wait-health --timeout 600
$env:LLM_BACKEND = "gpu"
.\.venv\Scripts\python.exe scripts\llm_gpu_smoke.py --health-only --generate
```

With API in Compose (`--profile ui --profile gpu`), set in `.env`:

```env
LLM_BACKEND=gpu
GPU_LLM_MODEL_ID=qwen/qwen2.5-0.5b-instruct
```

Compose assigns `GPU_LLM_BASE_URL=http://nim-llm:8000` inside the API container independently
of host-side `GPU_LLM_BASE_URL`. Override that container route only with
`GPU_LLM_CONTAINER_BASE_URL`.
Remove or unset `LLM_BACKEND=gpu` after the manual smoke when running the default
local test suite, so unrelated tests do not call the live GPU backend.

## Manual smoke checklist (required for PS5.3 Done)

Copy into PR and check all (`make` targets may be replaced with the documented
PowerShell equivalent on Windows):

- [x] Start NIM (`make gpu-up` or documented PowerShell equivalent) → container healthy
- [x] Health smoke against `http://localhost:8005/v1/health/ready` → HTTP 200
- [x] Gateway generate smoke → `backend_actual=gpu`, non-empty content
- [x] After generate via **containerized API** (`POST /runs`), host file `./var/llm_last_gpu_call_at` updated

## smoke-log

Successful evidence:

```text
timestamp: 2026-05-27T10:39:39+00:00
hardware: NVIDIA GeForce RTX 5070 Laptop GPU, 8151 MiB VRAM
nim runtime image: nvcr.io/nim/microsoft/phi-4-mini-instruct:1.12.0
served checkpoint: hf://Qwen/Qwen2.5-0.5B-Instruct
served model: qwen/qwen2.5-0.5b-instruct
health: OK (http://localhost:8005/v1/health/ready)
host generate: backend_actual=gpu content_len=12
containerized API: status=completed run_id=f56d378e7ddf4b4a8fac64f297801ae1
activity: ./var/llm_last_gpu_call_at updated from 2026-05-26T19:18:12+00:00 to 2026-05-27T10:39:39+00:00
operator note: GNU Make was not installed on the Windows host; documented equivalent commands were used.
```

### Llama 3.1 8B attempts 2026-05-26 - rejected by available VRAM

- Image: `nvcr.io/nim/meta/llama-3.1-8b-instruct:1.8.0-RTX`
- Hardware: `NVIDIA GeForce RTX 5070 Laptop GPU`, `8151 MiB` total VRAM
- Initial result: NIM detected `0 compatible profile(s)` and did not reach health/readiness.
- Retry: `NIM_RELAX_MEM_CONSTRAINTS=1` was accepted, but NIM estimated
  `13,563,402,752` bytes required on one GPU and again reported `0 compatible profile(s)`.
- Phi-4 follow-up: `microsoft/phi-4-mini-instruct:1.12.0` selected a compatible
  `sglang` profile but its BF16 weights occupied `6.75 GB` and left insufficient
  memory for KV cache.
- Resolution path: the local served checkpoint is reduced further to
  `Qwen/Qwen2.5-0.5B-Instruct` under the NIM `1.12.0` runtime.

## CI

Default PR CI does **not** start NIM (no GPU on runners). Optional workflow:
`.github/workflows/gpu-smoke.yml` (`workflow_dispatch` only).

For PS5.7 containerized API activity acceptance:

```bash
make gpu-idle-integration
```

This starts `nim-llm` and `api` under the `gpu` profile, posts one `/runs` request, verifies that
host file `./var/llm_last_gpu_call_at` is fresh, and confirms `gpu_idle_shutdown.py --dry-run`
reports `would_stop=false`.

## Idle TTL (PS5.7)

Use host-side scripts to decide whether NIM should be stopped after inactivity:

```bash
scripts/gpu_idle_shutdown.sh --dry-run
```

```powershell
.\scripts\gpu_idle_shutdown.ps1 -DryRun
```

Both read host file `./var/llm_last_gpu_call_at` (container path `/app/var/llm_last_gpu_call_at`
through `./var:/app/var` bind mount). Dry-run prints last activity, TTL, and `would_stop` decision
without stopping containers.

## Related

- Gateway contract: [llm_gateway.md](llm_gateway.md)
- PS5.4 health/fallback (next)
- PS5.7 idle TTL uses `llm_last_gpu_call_at`
