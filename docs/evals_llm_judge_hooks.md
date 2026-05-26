# Optional LLM-as-judge eval hooks (PS4.4, non-blocking)

SpaceOps **hard gates** use deterministic rubrics (`score_case`, semantic fixtures, injection suite). Some quality dimensions (report clarity, operator usefulness, nuanced grounding) may eventually need **semantic judges** (LLM-as-judge, RAGAS-style, LangSmith evaluators).

**Status:** documented only — **not required for merge** and not wired in CI today.

## When to consider a judge

- String-equality checks are insufficient (e.g. paraphrased executive summary still correct).
- You need trend comparison across model versions beyond MoE counters.
- Human review load is high and you want a **soft signal** before release.

## Proposed integration (future)

1. **Separate job** `evals-judge-soft` with `continue-on-error: true` (same tier as `evals-soft`).
2. **Input:** frozen run artifacts (`data/incidents/run_*.json`) or eval case outputs.
3. **Output:** JSON scores appended to `eval-judge-summary.json` artifact.
4. **Policy:** failures do not block merge; appear in release notes / PS4.7 soft signals.

## Guardrails

- Judges must not replace `semantic-evals`, `safety-gates`, or `eval-injection-suite` hard gates.
- Pin judge model + prompt version (prompt registry pattern, S3.2).
- Rate-limit cost; run on schedule or main-only, not every fork.

## References

- [evals/README.md](../evals/README.md) — deterministic suites  
- [docs/runbooks/ci_gating_policy.md](runbooks/ci_gating_policy.md) — hard vs soft gates  
- Shadow models: [docs/shadow_models.md](shadow_models.md)
