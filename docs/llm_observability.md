## LLM observability spine (S3.0)

S3.0 introduces a lightweight, Langfuse-compatible observability spine for LLM calls. The
goal is to have a consistent internal model and API for:

- runs (`run_id` aligned with trace / incident where possible),
- LLM calls (node, model, prompt, metrics),
- eval / injection metadata,

without depending on a specific external tool. A later phase (02-production-scale) can map
this spine to a full Langfuse deployment or another observability backend.

### Data model

- **Runs** (`data/llm_runs/runs.ndjson`)
  - one JSON line per logical run:
    - `timestamp`: ISO-8601 UTC
    - `run_id`: string (UUID4 hex or caller-provided)
    - `metadata`: free-form dict (e.g. `incident_id`, `node`, `eval_case_id`, `kind`)

- **LLM calls** (`data/llm_runs/llm_calls.ndjson`)
  - one JSON line per LLM call (currently wired to triage/decide):
    - `timestamp`
    - `run_id`
    - `node`: e.g. `triage`, `decide`
    - `model_id`: e.g. `gpt-4o-mini`
    - `prompt_id`: e.g. `triage`, `decide`
    - `prompt_version`: e.g. `v1`
    - `tags`: optional dict (context such as subsystem/risk)
    - `metrics`: optional dict (e.g. `tokens_used`)
    - `eval_case_id` / `injection_case_id`: optional when called from evals

The same metadata is also mirrored as **OTel span attributes** (`llm.run_id`, `llm.node`,
`llm.model_id`, `llm.prompt_id`, etc.) when tracing is enabled.

### API surface

Module: `apps.llm_observability`:

- `start_llm_run(run_id: str | None = None, **metadata) -> str`
  - ensures there is a logical `run_id`,
  - appends a record to `runs.ndjson`,
  - never raises (best-effort).

- `log_llm_call(run_id: str, *, node: str, model_id: str, prompt_id: str, prompt_version: str | None = None, tags: dict | None = None, metrics: dict | None = None, eval_case_id: str | None = None, injection_case_id: str | None = None) -> None`
  - appends a record to `llm_calls.ndjson`,
  - annotates the current OTel span (if any) with `llm.*` attributes,
  - never raises (best-effort).

### Current usage

- **Agent nodes** (`apps/agent/nodes.py`):
  - `triage`:
    - calls `start_llm_run(trace_id, incident_id=..., node="triage")`,
    - after `_chat_completion`, calls `log_llm_call(..., node="triage", model_id="gpt-4o-mini", prompt_id="triage", prompt_version="v1", metrics={"tokens_used": usage})`.
  - `decide`:
    - calls `start_llm_run(trace_id, incident_id=..., node="decide")`,
    - after `_chat_completion`, calls `log_llm_call(..., node="decide", model_id="gpt-4o-mini", prompt_id="decide", prompt_version="v1", tags={"subsystem": subsystem, "risk": risk}, metrics={"tokens_used": usage})`.

- **Evals** (`evals/scoring.py`):
  - `run_case`:
    - calls `start_llm_run(case_id, eval_case_id=case_id, kind="standard_eval")` before `run_pipeline`.
  - `run_injection_case`:
    - calls `start_llm_run(case_id, eval_case_id=case_id, injection_case_id=doc_name, kind="injection_eval")` before `run_pipeline`.

### Relation to Langfuse

The fields above map naturally to a Langfuse-style schema:

- `run_id` ↔ trace/run identifier,
- `node` ↔ span / step name,
- `model_id` ↔ model,
- `prompt_id` / `prompt_version` ↔ prompt registry entries,
- `eval_case_id` / `injection_case_id` ↔ experiment identifiers.

In 02-production-scale, an adapter can be added that forwards these events to Langfuse
while keeping agent / eval code unchanged.

