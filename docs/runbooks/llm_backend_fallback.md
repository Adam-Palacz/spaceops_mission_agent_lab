# LLM backend fallback runbook (PS5.4)

This runbook explains how to distinguish:

- GPU backend serving normally (`backend_actual=gpu`)
- GPU unhealthy/circuit-open with successful fallback (`backend_actual=openai`)
- total outage (GPU unavailable and OpenAI fallback unavailable)

## Signals to check

- Gateway structured logs (`apps.llm_gateway`):
  - `backend_requested`
  - `backend_actual`
  - `fallback_used`
  - `fallback_reason`
- Prometheus counter:
  - `llm_backend_fallback_total{from_backend="gpu",to_backend="openai",reason=...}`

## Expected behaviors

### 1) GPU serving OK

- `backend_requested=gpu`
- `backend_actual=gpu`
- `fallback_used=false`
- `fallback_reason=""`

### 2) GPU unhealthy, fallback active

- `backend_requested=gpu`
- `backend_actual=openai`
- `fallback_used=true`
- `fallback_reason` in:
  - `gpu_unhealthy` (readiness probe failed)
  - `gpu_circuit_open` (breaker open)
  - `gpu_timeout` (GPU request timed out)
  - `gpu_error` (provider/transport error)

`llm_backend_fallback_total` should increment once per fallback call.

### 3) GPU unavailable and no OpenAI fallback

- Generate call raises `LLMGatewayProviderError`.
- Typical cause: missing `OPENAI_API_KEY` while `LLM_BACKEND=gpu`.

## Operator actions

1. Check NIM readiness:
   - `curl -sf http://localhost:8005/v1/health/ready`
2. Check fallback pressure:
   - monitor increase in `llm_backend_fallback_total`.
3. If fallback remains high:
   - inspect `spaceops-nim-llm` logs
   - verify `GPU_LLM_BASE_URL`/container routing
   - confirm GPU memory/headroom on host
4. If both GPU and OpenAI are unavailable:
   - restore `OPENAI_API_KEY` and/or set `LLM_BACKEND=openai` temporarily.

## Important guardrail

`LLMBudgetExceededError` is **not** a fallback condition.
Budget rejections must propagate unchanged (`reason=budget_exceeded`) without retrying on another backend.
