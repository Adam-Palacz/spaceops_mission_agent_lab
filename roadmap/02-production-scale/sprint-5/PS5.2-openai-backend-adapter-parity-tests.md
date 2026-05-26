# PS5.2 — OpenAI backend adapter parity tests

| Field | Value |
|-------|-------|
| **Task ID** | PS5.2 |
| **Status** | Todo |

---

## Description

Treat **`LLM_BACKEND=openai`** as the **reference cloud backend**: lock behavior with contract tests,
structured metadata logging, and a baseline for PS5.8 parity comparisons. Ensures refactors in
PS5.1 do not regress production paths.

**Note:** `cursor_sh` is a separate backend adapter (same registry); this task owns the `openai`
adapter only. Correlation with `run_id` stays in existing **`llm_observability`** / node spans —
PS5.2 does **not** require `run_id` on `generate()` (optional `trace_context` is PS5.1-only).

---

## Requirements

- [ ] OpenAI adapter selected when `LLM_BACKEND=openai` (or unset / legacy `LLM_PROVIDER=openai` only).
- [ ] Metadata logged on every call: `node`, `provider`, `model_id`, `latency_ms`, token usage, plus PS5.1 backend metadata fields.
- [ ] Optional cost estimate field (tokens × configured rate table) — may be `0` if unknown.
- [ ] Tests use HTTP mocking (no live API key required for CI).
- [ ] Document env vars: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_CHAT_COMPLETIONS_PATH`.

---

## Dependencies

- **PS5.1** — registry layout, response metadata, configuration precedence.

---

## Checklist

- [ ] Extract OpenAI HTTP client into dedicated adapter module.
- [ ] Add golden/fixture tests for normalized response parsing (usage, empty choices, malformed JSON).
- [ ] Confirm `start_llm_run` / OTel paths unchanged — gateway logs `node` + backend metadata only.
- [ ] Align with `docs/shadow_models.md` — production model id comes from `AGENT_MODEL_ID`.

---

## Test / acceptance

- [ ] CI: OpenAI adapter unit tests pass without secrets.
- [ ] Manual smoke: one `POST /runs` with `LLM_BACKEND=openai` produces expected log line shape.
- [ ] Parity fixture documents expected metadata keys for PS5.8 comparison.

---

## Deliverables (expected)

- `apps/llm_backends/openai.py` (or equivalent)
- `tests/test_llm_openai_adapter_ps52.py`
- `tests/fixtures/llm/openai_chat_completion.json` (sample payload)
- `docs/llm_gateway.md` — OpenAI section + metadata table
