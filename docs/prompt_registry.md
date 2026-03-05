## Prompt registry (S3.2)

S3.2 introduces a central prompt registry so that core prompts are no longer only inline in
agent code. Prompts are referenced by ID and version, which also flow into the LLM
observability spine (S3.0).

### Where prompts live

- Module: `prompts/registry.py`
  - Defines:
    - `Prompt` dataclass (`id`, `version`, `description`, `text`)
    - an internal `_PROMPTS` dict keyed by prompt id
    - `get_prompt(prompt_id: str) -> Prompt`
    - constants `TRIAGE_PROMPT_ID`, `DECIDE_PROMPT_ID`

Example entries:

- `triage` v1 — classifies incident into subsystem and risk.
- `decide` v1 — produces a short, citation-grounded action plan.

### How agent nodes use the registry

- In `apps/agent/nodes.py`:
  - `triage`:
    - imports `TRIAGE_PROMPT_ID` and `get_prompt`
    - calls `triage_prompt = get_prompt(TRIAGE_PROMPT_ID)`
    - formats the prompt with `payload` and `subsystems`, then passes the resulting string
      to `_chat_completion`.
    - passes `triage_prompt.id` and `triage_prompt.version` into `log_llm_call(...)` so
      observability records the prompt version used.
  - `decide`:
    - imports `DECIDE_PROMPT_ID` and `get_prompt`
    - calls `decide_prompt = get_prompt(DECIDE_PROMPT_ID)`
    - formats the prompt with `subsystem`, `risk`, `investigation_notes`, `doc_ids`,
      `snippet_ids`, then calls `_chat_completion`.
    - uses `decide_prompt.id` / `version` for `log_llm_call(...)`.

### How to change a prompt

1. Edit the appropriate entry in `prompts/registry.py`:
   - Update the `text` field.
   - If the change is behaviourally meaningful, bump the `version` (e.g. from `v1` to `v2`).
2. Run evals and/or shadow tests to detect regressions:
   - `python -m evals.scoring` (standard + injection evals).
   - Optionally: `python -m evals.shadow_models` if you are testing prompts together with
     model changes.
3. Inspect:
   - `data/llm_runs/llm_calls.ndjson` and OTel traces (Jaeger) to confirm that `prompt_id`
     and `prompt_version` reflect the updated prompt.

### Future extensions

- Add more prompt ids for `investigate`, `report`, `act`, and eval-specific prompts.
- Move `_PROMPTS` to a YAML or JSON file under `prompts/` and keep `registry.py` as a thin
  loader/validator.
- Allow evals to reference prompts by id (e.g. in cases.yaml) for finer-grained prompt
  experiments.

