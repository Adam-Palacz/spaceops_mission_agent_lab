# PS5.3 — Optional GPU backend adapter (NVIDIA NIM)

| Field | Value |
|-------|-------|
| **Task ID** | PS5.3 |
| **Status** | Done |

---

## Description

Add an **optional** GPU inference backend behind the same `generate()` contract. GPU is **off by
default**; local/dev uses `LLM_BACKEND=openai` unless `--profile gpu` is enabled.

**Sprint decision (fixed runtime):** [**NVIDIA NIM**](https://docs.nvidia.com/nim/) with
**OpenAI-compatible** `/v1/chat/completions` and health via **`GET /v1/health/ready`** (or
documented NIM equivalent). Triton/custom shims and “placeholder only” compose services are
**out of scope** for PS5.3 Done — defer to Phase 7 if needed.

Parent: [Phase 5 — LLM Backends](../../02-production-scale.md#phase-5--llm-backends-vendor-agnostic--optional-gpu-off-by-default).

---

## Requirements

- [x] `LLM_BACKEND=gpu` routes to NIM base URL + model id (`GPU_LLM_BASE_URL`, `GPU_LLM_MODEL_ID`).
- [x] Compose profile `gpu` runs **real NIM image** (pinned tag in compose) + wires env to API/agent.
- [x] **`api` service bind mount:** `./var:/app/var` so PS5.7 idle TTL sees `llm_last_gpu_call_at` from host.
- [x] `GPU_ACTIVITY_FILE` resolves to `/app/var/llm_last_gpu_call_at` inside the API container and `./var/llm_last_gpu_call_at` on the host (see PS5.7).
- [x] Health probe matches NIM (`/v1/health/ready` or documented path) — consumed by PS5.4.
- [x] No GPU container on default `docker compose up` (profile isolated).
- [x] `make gpu-up` / `make gpu-down` for operator workflow.
- [x] Gateway sets **`backend_actual=gpu`** only when NIM served the request (not fallback).

---

## Done evidence (required — not optional)

PS5.3 is **not** Done with mocked HTTP alone. PR must include:

1. **Automated:** unit tests for adapter URL/payload (mocked).
2. **Manual smoke checklist** (copy into PR), all checked; on Windows, documented
   direct PowerShell commands are equivalent when GNU Make is unavailable:
   - [x] NIM started via documented Compose command → container healthy
   - [x] Script health endpoint check returns HTTP 200
   - [x] `scripts/llm_gpu_smoke.py --generate` → one `generate()` returns non-empty `content` and `backend_actual=gpu`
   - [x] After smoke via **containerized API**, `./var/llm_last_gpu_call_at` on **host** is updated (PS5.7 mount check)
3. **Optional CI:** `.github/workflows/gpu-smoke.yml` with `workflow_dispatch` only (not PR blocker).

Record smoke output (redacted) in PR or `docs/llm_gpu_backend.md#smoke-log`.

---

## Dependencies

- **PS5.1** — backend registry + metadata fields.
- **PS5.4** — health + fallback (parallel after NIM compose exists).

---

## Checklist

- [x] `infra/docker-compose.yml` — `gpu` profile with pinned NIM service + model env.
- [x] GPU adapter: same request/response normalization as OpenAI adapter.
- [x] `.env.example` — `GPU_LLM_BASE_URL`, `GPU_LLM_MODEL_ID`, NIM license note if applicable.
- [x] `docs/llm_gpu_backend.md` — NIM-only setup (no Triton branch in Done criteria).
- [x] `scripts/llm_gpu_smoke.py` — health + single completion for operators.

---

## Test / acceptance

- [x] Unit test: GPU adapter builds correct URL/headers from settings (mocked HTTP).
- [x] Manual smoke checklist completed (see **Done evidence**) — operator with GPU + NGC.
- [x] Default CI unchanged when GPU profile not started.
- [x] Sprint DoD item “`LLM_BACKEND=gpu` works through gateway” satisfied after real smoke passed.

### Model adjustment after validation (2026-05-26)

- Tested image: `nvcr.io/nim/meta/llama-3.1-8b-instruct:1.8.0-RTX`.
- Tested hardware: `NVIDIA GeForce RTX 5070 Laptop GPU`, `8151 MiB` VRAM.
- Tested both default memory checks and `NIM_RELAX_MEM_CONSTRAINTS=1`.
- NIM still reported `0 compatible profile(s)`; with relaxed constraints it estimated
  `13,563,402,752` bytes required on one GPU, exceeding available VRAM.
- `microsoft/phi-4-mini-instruct:1.12.0` selected a compatible profile but its
  BF16 weights consumed `6.75 GB`, leaving insufficient memory for KV cache.
- The local NIM runtime remains `1.12.0`, while its served checkpoint is reduced to
  `Qwen/Qwen2.5-0.5B-Instruct` (`0.49B` parameters); real smoke passed with
  `backend_actual=gpu` and host-visible activity timestamp update.

---

## Deliverables (expected)

- `apps/llm_backends/gpu.py` — NIM OpenAI-compatible client
- `infra/docker-compose.yml` — `gpu` profile (NIM)
- `Makefile` — `gpu-up`, `gpu-down`
- `docs/llm_gpu_backend.md`
- `scripts/llm_gpu_smoke.py`
- `tests/test_llm_gpu_adapter_ps53.py`

---

## Out of scope (defer)

- Triton, custom OpenAI shims, placeholder images without NIM.
- Multi-GPU scheduling, cloud burst (Phase 7).
