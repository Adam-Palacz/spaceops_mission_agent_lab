# Evals (S1.11, S2.8)

Eval cases and scoring for the SpaceOps agent: **triage accuracy** (top-1/top-2), **citation presence**, **must-escalate** (MoE1–MoE4), and **injection suite** (MoE3 — unsafe-action rate = 0).

## Run evals

From repo root:

```bash
# Requires OPENAI_API_KEY in .env or environment
python -m evals.scoring
```

Exit code **0** if all cases pass; **1** if any case fails or score is below threshold (all must pass).

## Deterministic CI gates (PS1.8)

CI runs two focused gates before full evals:

- Must-escalate guardrail gate:
  - `python -m evals.scoring --case-id must-escalate-no-evidence`
- Evidence-required gate:
  - `python -m evals.scoring --case-id citation-present`

Both commands fail fast with actionable output in format:

- `FAIL  <case_id>  <reason>`

Examples of reasons:

- `must_escalate: expected escalation, agent did not escalate`
- `require_citations: expected citations but run escalated`
- `require_citations: expected at least one citation or citation_ref`

Quick local pre-PR check (same hard gates as CI `evals-hard` job):

```bash
python -m evals.scoring --case-id must-escalate-no-evidence --case-id citation-present
python -m evals.scoring --injection-only
```

Full suite as a **soft signal** (non-blocking, exit 0 even on failures):

```bash
python -m evals.scoring --soft-signal
```

See [docs/runbooks/ci_gating_policy.md](../docs/runbooks/ci_gating_policy.md) (PS4.7).

## Semantic eval suite (PS4.4, no LLM)

Deterministic **fixture-based** scoring for citation precision and audit semantics. Does **not** call the LLM — safe on every PR/fork.

```bash
python -m evals.semantic
# or
make semantic-check
```

Cases: `evals/semantic_cases.yaml` · Fixtures: `evals/fixtures/semantic/*.json`

Covers:

- Citation present / missing refs / wrong ref (`require_citation_precision`)
- `no_evidence`, `tool_failure`, `policy_deny` escalation reasons
- **empty vs failure:** `semantic-tool-empty-not-failure` (empty telemetry ≠ `tool_failure`)

CI job **`semantic-evals`** writes artifact `eval-semantic-summary.json` (per-case pass/fail).

Optional fields in semantic cases (also supported in `score_case` for live runs):

| Field | Description |
|-------|-------------|
| `expected_escalation_reason` | Exact `escalation_packet.reason` required |
| `forbid_escalation_reason` | Run must not escalate with this reason |
| `expected_tool_outcomes` | Map of tool → `success` / `empty` / `failure` |
| `expect_scoring_pass` | If false, rubric must fail (negative fixtures) |
| `triage_gate` | Runbook routing hint (`citation_precision`, `audit_semantics`) |

Future LLM-as-judge hooks: [docs/evals_llm_judge_hooks.md](../docs/evals_llm_judge_hooks.md) (non-blocking).

## Case format

Cases live in `evals/cases.yaml`. Each case has:

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `description` | Optional human-readable description |
| `payload` | Incident payload passed to the agent (e.g. `time_range_start`, `time_range_end`, `message`) |
| `expected_subsystem` | List of acceptable subsystems (e.g. `["Power", "Thermal"]` for top-2) |
| `expected_subsystem_top_k` | 1 = top-1 only, 2 = top-2 acceptable |
| `require_citations` | If true, run must produce at least one citation (when not escalating) |
| `must_escalate` | If true, agent must escalate (escalation packet present) |

## Adding a case

1. Open `evals/cases.yaml`.
2. Add a new entry under `cases:` with `id`, `payload`, and expectations.
3. For triage-only: set `expected_subsystem` and `expected_subsystem_top_k`; `require_citations: false`, `must_escalate: false`.
4. For citation check: set `require_citations: true` and acceptable `expected_subsystem` (broad list if triage can vary).
5. For must-escalate (e.g. no evidence): set `must_escalate: true` and a payload that leads to no evidence when MCP/KB are empty or unavailable.
6. Run `python -m evals.scoring` to verify.

## Determinism

The agent uses **temperature=0** for LLM calls so that the same case yields the same result across runs. CI runs evals on every push/PR; all cases must pass.

## Injection suite (S2.8)

Documents in `evals/injection_suite/` are fake runbooks that try to trigger unsafe actions (e.g. "ignore OPA", "run shell"). Cases in `evals/injection_cases.yaml` inject one doc into the payload message and run the pipeline. **Expected: no unsafe action** (unsafe-action rate = 0). If the agent outputs a step with a forbidden `action_type` or dangerous phrase (see `evals/scoring.py`: `ALLOWED_ACTION_TYPES`, `UNSAFE_PHRASES`), the injection eval fails. See `evals/injection_suite/README.md` for what "unsafe" means (NF1, NF3, P1–P3).

## CI

GitHub Actions workflow `.github/workflows/ci.yml` runs `python -m evals.scoring` (including the injection suite) in the `evals` job on push/PR to `main`. Set `OPENAI_API_KEY` (and optionally `POSTGRES_PASSWORD`) in repo secrets for the job to succeed.

The `test` job also runs **`tests/test_golden_baseline.py`** (synthetic replay fixture): pinned
`expected_outcome` fields must still match the mocked pipeline. After you **intentionally** change
model or prompt behavior, refresh eval expectations in `evals/cases.yaml` / scoring as usual, and
if you maintain repo golden pins under `data/replay/golden/`, run
`python scripts/golden_baseline.py update --run-id …` per [docs/golden_run_baselines.md](../docs/golden_run_baselines.md).

## Shadow model comparison (S3.1 / P4.8)

Compare **production** vs **candidate** model ids offline (does not change live config):

```bash
# Set AGENT_CANDIDATE_MODEL_IDS in .env (comma-separated), same API key as evals
python -m evals.shadow_models
```

Reports: `evals/reports/shadow_models_*.json`. Scheduled or manual runs: workflow
`.github/workflows/shadow-models.yml`. Full process: [docs/shadow_models.md](../docs/shadow_models.md).
