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

## Extension

- Add backends in `apps/llm_backends/` and register in `registry.py`.
- PS5.4 adds GPU health/fallback; PS5.6 adds budget enforcement before `generate()` returns.
