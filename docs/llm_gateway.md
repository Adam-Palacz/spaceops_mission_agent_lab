# LLM gateway contract (PS1.6, PS5.1)

`apps/llm_gateway.py` is the single integration point for LLM calls used by agent nodes and
helpers. Backend HTTP logic lives in `apps/llm_backends/`.

## Purpose

- keep provider-specific HTTP out of nodes;
- normalize response shape and backend metadata;
- explicit timeout/provider/budget failure semantics;
- structured logging (model, backend, latency, tokens).

## Interface

```python
generate(
    prompt: str,
    node: str,
    model_id: str | None = None,
    temperature: float = 0,
    trace_context: dict | None = None,  # optional; OTel correlation at node layer
) -> dict
```

### Normalized response

| Field | Description |
|-------|-------------|
| `content` | Model text |
| `model_id` | Model used |
| `provider` | **Alias** of `backend_actual` (backward compatible) |
| `latency_ms` | Round-trip ms |
| `usage` | `prompt_tokens`, `completion_tokens`, `total_tokens` |
| `backend_requested` | Resolved `LLM_BACKEND` |
| `backend_actual` | Adapter that served the call |
| `fallback_used` | `false` in PS5.1 (PS5.4 sets fallback) |
| `fallback_reason` | Empty when no fallback |
| `estimated_cost_usd` | OpenAI arm only when rate card set (PS5.2); else `0.0` |

## OpenAI backend (PS5.2 — reference cloud arm)

Implementation: `apps/llm_backends/openai.py`. Selected when `LLM_BACKEND=openai`, unset config
(default), or legacy `LLM_PROVIDER=openai` only.

| Env | Required | Description |
|-----|----------|-------------|
| `OPENAI_API_KEY` | yes | Bearer token for chat completions |
| `OPENAI_BASE_URL` | no | Default `https://api.openai.com` |
| `LLM_CHAT_COMPLETIONS_PATH` | no | Default `/v1/chat/completions` |
| `LLM_OPENAI_COST_PER_1K_TOKENS` | no | USD per 1k tokens → `estimated_cost_usd`; `0` = disabled |
| `AGENT_MODEL_ID` | no | Default model when `generate(model_id=None)` |

**Logging:** `apps/llm_gateway.py` logs `node`, `provider`, `backend_requested`, `backend_actual`,
`outcome`, `model_id`, `latency_ms`, `total_tokens`, `estimated_cost_usd`. Failed attempts log
`backend_actual=unserved`, `outcome=error`, and `error_type`, because no backend successfully
served that call. Run correlation uses existing `llm_observability` / OTel at the node layer.

**PS5.8 parity baseline:** `tests/fixtures/llm/openai_parity_metadata_baseline.json`

**Manual smoke:** `LLM_BACKEND=openai` + `POST /runs` → log line contains
`llm_gateway_call ... backend_actual=openai ... estimated_cost_usd=`.

## Configuration (PS5.1)

| Knob | Env | Values |
|------|-----|--------|
| **Backend** | `LLM_BACKEND` | `openai` \| `cursor_sh` \| `gpu` |
| **Legacy** | `LLM_PROVIDER` | `openai` \| `cursor_sh` (deprecated) |

**Precedence**

1. `LLM_BACKEND` set → use it (`LLM_PROVIDER` ignored; one-time warning if both set).
2. Only `LLM_PROVIDER` → map to same backend value; deprecation warning.
3. Neither → `openai`.

| Backend | Credentials / URL |
|---------|-------------------|
| `openai` | `OPENAI_API_KEY`, `OPENAI_BASE_URL` |
| `cursor_sh` | `CURSOR_SH_API_KEY`, `CURSOR_SH_BASE_URL` |
| `gpu` | `GPU_LLM_BASE_URL`, `GPU_LLM_MODEL_ID`, optional `GPU_LLM_API_KEY`; configured GPU model takes precedence over the generic agent model |

## Failure semantics

| Exception | When | Node escalation |
|-----------|------|-----------------|
| `LLMGatewayTimeoutError` | HTTP timeout | `llm_timeout` |
| `LLMGatewayProviderError` | Provider/HTTP error | `llm_provider_error` |
| `LLMBudgetExceededError` | Budget guard (PS5.6) | `budget_exceeded` — **no backend fallback** |

## URL normalization

- `LLM_CHAT_COMPLETIONS_PATH` appended when base URL is not already a full `/chat/completions` endpoint.

## GPU / NIM (PS5.3)

See **[llm_gpu_backend.md](llm_gpu_backend.md)** for Compose profile `gpu`, `make gpu-up`, and smoke checklist.

## Extension

- Add backends in `apps/llm_backends/` and register in `registry.py`.
- PS5.4 adds GPU health/fallback; PS5.6 adds budget enforcement before `generate()` returns.
