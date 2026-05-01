# Shadow model testing and promotion (P4.8)

This describes how we **compare the production LLM** (`agent_model_id`) against **candidate
models** before changing config, without touching live traffic. The comparison uses the same
standard and injection eval suites as production-quality gates, run **offline** from the
repo.

## When to run

- **Before** changing `AGENT_MODEL_ID` / `agent_model_id` in config or GitOps.
- **After** vendor deprecations, pricing changes, or prompt/agent changes that might interact
  differently with a new model.
- On a **schedule** (weekly smoke) via GitHub Actions, if secrets are configured — see
  `.github/workflows/shadow-models.yml`.

Normal PR CI (`.github/workflows/ci.yml`) continues to run `evals.scoring` only; shadow runs
are **separate** so they do not block unrelated merges and only gate model promotion decisions.

## How to run locally

1. Set LLM credentials (same as evals): e.g. `OPENAI_API_KEY` in `.env`.
2. Set **`AGENT_CANDIDATE_MODEL_IDS`** to one or more comma-separated model ids (e.g.
   `gpt-4o,gpt-4o-mini`). Keep **`AGENT_MODEL_ID`** as today’s production model.
3. Start the Telemetry MCP server if your cases need it (same as CI evals job), then:

```bash
python -m evals.shadow_models
```

Reports are written under **`evals/reports/`** as `shadow_models_<timestamp>.json` (see
[evals/reports/README.md](../evals/reports/README.md)). Generated files are gitignored; CI
uploads them as **workflow artifacts** on the *Shadow models* workflow.

**Sample shape (static, not a live run):** [evals/reports/sample_shadow_report.json](../evals/reports/sample_shadow_report.json).

## How to read the report

- **`baseline`**: standard + injection results for the current production model id, including
  **`wall_clock_seconds`** per phase (rough wall time for that eval pass).
- **`candidates`**: same structure per candidate model id.
- **`decision`**: automated gate output (see below).

Per-case detail is under `baseline.standard.cases`, `candidates[].standard.cases`, and
injection counterparts — use these to debug a failure without re-running all models.

## Decision rules (automated gate)

The script exits **0** only if **every** candidate satisfies all of:

1. **Standard evals — no regression:** candidate `standard.score` (fraction of passed cases)
   must be **≥** baseline `standard.score`. Anything lower fails the gate.
2. **Injection — zero unsafe:** candidate `injection.unsafe_cases` must be **0**.

**Not automated (human review):**

- **Latency / cost:** compare `wall_clock_seconds` and your LLM observability (tokens, spend)
  against SLOs and budget. The report documents this under `decision.rules.latency_and_cost`.

The **`decision.candidates`** array lists `promote_ok` per model plus flags for regression
and injection failure.

## Who decides

- **Engineering owner** (or on-call for the agent) runs shadow evals and attaches the JSON
  (or CI artifact link) to the change request (PR / ticket).
- **Promotion** merges the config change to `agent_model_id` only when the automated gate is
  green **and** latency/cost/sign-off criteria from your team are met.

## Related

- Implementation: [`evals/shadow_models.py`](../evals/shadow_models.py)
- Config fields: `agent_model_id`, `agent_candidate_model_ids` in `config.py` / `.env.example`
- Production-scale context: [roadmap/02-production-scale.md](../roadmap/02-production-scale.md)
- Process index: [docs/process.md](process.md)
