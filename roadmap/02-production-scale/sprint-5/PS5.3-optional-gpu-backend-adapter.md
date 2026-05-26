# PS5.3 — Optional GPU backend adapter (NVIDIA NIM)

| Field | Value |
|-------|-------|
| **Task ID** | PS5.3 |
| **Status** | Todo |

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

- [ ] `LLM_BACKEND=gpu` routes to NIM base URL + model id (`GPU_LLM_BASE_URL`, `GPU_LLM_MODEL_ID`).
- [ ] Compose profile `gpu` runs **real NIM image** (pinned tag in compose) + wires env to API/agent.
- [ ] **`api` service bind mount:** `./var:/app/var` so PS5.7 idle TTL sees `llm_last_gpu_call_at` from host.
- [ ] `GPU_ACTIVITY_FILE` default `/app/var/llm_last_gpu_call_at` inside container (see PS5.7).
- [ ] Health probe matches NIM (`/v1/health/ready` or documented path) — consumed by PS5.4.
- [ ] No GPU container on default `docker compose up` (profile isolated).
- [ ] `make gpu-up` / `make gpu-down` for operator workflow.
- [ ] Gateway sets **`backend_actual=gpu`** only when NIM served the request (not fallback).

---

## Done evidence (required — not optional)

PS5.3 is **not** Done with mocked HTTP alone. PR must include:

1. **Automated:** unit tests for adapter URL/payload (mocked).
2. **Manual smoke checklist** (copy into PR), all checked:
   - [ ] `make gpu-up` → NIM container healthy
   - [ ] `curl` (or script) health endpoint returns 200
   - [ ] `python -m scripts.llm_gpu_smoke` (or documented one-liner) → one `generate()` returns non-empty `content` and `backend_actual=gpu`
   - [ ] After smoke via **containerized API**, `./var/llm_last_gpu_call_at` on **host** is updated (PS5.7 mount check)
3. **Optional CI:** `.github/workflows/gpu-smoke.yml` with `workflow_dispatch` only (not PR blocker).

Record smoke output (redacted) in PR or `docs/llm_gpu_backend.md#smoke-log`.

---

## Dependencies

- **PS5.1** — backend registry + metadata fields.
- **PS5.4** — health + fallback (parallel after NIM compose exists).

---

## Checklist

- [ ] `infra/docker-compose.yml` — `gpu` profile with pinned NIM service + model env.
- [ ] GPU adapter: same request/response normalization as OpenAI adapter.
- [ ] `.env.example` — `GPU_LLM_BASE_URL`, `GPU_LLM_MODEL_ID`, NIM license note if applicable.
- [ ] `docs/llm_gpu_backend.md` — NIM-only setup (no Triton branch in Done criteria).
- [ ] `scripts/llm_gpu_smoke.py` — health + single completion for operators.

---

## Test / acceptance

- [ ] Unit test: GPU adapter builds correct URL/headers from settings (mocked HTTP).
- [ ] Manual smoke checklist completed (see **Done evidence**).
- [ ] Default CI unchanged when GPU profile not started.
- [ ] Sprint DoD item “`LLM_BACKEND=gpu` works through gateway” satisfied **only** after smoke passes.

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
