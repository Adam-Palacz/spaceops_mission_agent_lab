# Evals (S1.11, S2.8)

Eval cases and scoring for the SpaceOps agent: **triage accuracy** (top-1/top-2), **citation presence**, **must-escalate** (MoE1–MoE4), and **injection suite** (MoE3 — unsafe-action rate = 0).

## Run evals

From repo root:

```bash
# Requires OPENAI_API_KEY in .env or environment
python -m evals.scoring
```

Exit code **0** if all cases pass; **1** if any case fails or score is below threshold (all must pass).

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
