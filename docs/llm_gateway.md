# LLM gateway contract (PS1.6)

`apps/llm_gateway.py` is the single integration point for provider calls used by
agent nodes.

## Purpose

- keep provider-specific HTTP logic out of nodes;
- normalize response shape for callers;
- provide explicit timeout/provider failure semantics;
- emit structured metadata (model/provider/latency/token usage).

## Interface

Function:

- `generate(prompt, node, model_id=None, temperature=0) -> dict`

Normalized response:

- `content` (str)
- `model_id` (str)
- `provider` (str)
- `latency_ms` (int)
- `usage`:
  - `prompt_tokens` (int)
  - `completion_tokens` (int)
  - `total_tokens` (int)

## Failure semantics

- timeout -> `LLMGatewayTimeoutError`
- other provider/backend errors -> `LLMGatewayProviderError`

Nodes map these failures into escalation paths (`llm_timeout`, `llm_provider_error`)
to preserve fail-closed behavior.

## Provider routing and URLs

Gateway endpoints are config-driven:

- `LLM_PROVIDER` (`openai` | `cursor_sh`)
- `OPENAI_BASE_URL`
- `CURSOR_SH_BASE_URL`
- `LLM_CHAT_COMPLETIONS_PATH`

Compatibility rule:

- if a base URL already ends with `/chat/completions`, gateway uses it as-is;
- otherwise gateway appends `LLM_CHAT_COMPLETIONS_PATH`.

## Extension points

- add new providers in `_provider_config()` without changing node logic;
- add per-node routing policy by using `node` argument and gateway-side mapping;
- enrich metadata output centrally (cost, request IDs, extra usage fields).
