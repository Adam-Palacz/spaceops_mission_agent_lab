# CI gating policy (PS4.7)

Defines which checks **block merge** (hard gates) vs **report only** (soft signals), how to recover from failures, and emergency override process.

**Workflow:** `.github/workflows/ci.yml`  
**Local runner:** `python scripts/ci_gate_runner.py --hard-only`  
**Makefile:** `make safety-gates`, `make check` (fast hard gates without Postgres/evals)

---

## Gate matrix

| Order | Gate ID | Tier | CI job | What it protects |
|------|---------|------|--------|------------------|
| 1 | `lint-ruff` | **hard** | `lint` | Style/errors (ruff) |
| 2 | `lint-mypy` | **hard** | `lint` | Type safety |
| 3 | `golden-baseline` | **hard** | `golden-check` | Replay regression (PS4.5) |
| 4 | `safety-opa-hitl` | **hard** | `safety-gates` | OPA fail-closed, approval path, evidence, injection, schema |
| 5 | `pytest-full` | **hard** | `test` | Full unit/integration + migrations |
| 6 | `docker-build` | **hard** | `docker-build` | Compose + images build |
| 7 | `eval-must-escalate` | **hard** | `evals-hard` | No silent run without evidence (PS1.8) |
| 8 | `eval-citation-present` | **hard** | `evals-hard` | Citations when required (PS1.8) |
| 9 | `eval-injection-suite` | **hard** | `evals-hard` | Unsafe-action rate = 0 (S2.8) |
| 10 | `evals-full-suite` | **soft** | `evals-soft` | Broader MoE quality (non-blocking) |

### OPA / HITL criteria (`safety-opa-hitl`)

Hard gate **must** pass these tests (fail-closed semantics):

- `tests/test_act_opa_policy.py` — OPA deny → `policy_deny` escalation, no approval request created
- `tests/test_opa_client.py` — OPA client unavailable → deny
- `tests/test_evidence_policy_ps41.py` — evidence policy violation escalates
- `tests/test_prompt_injection_ps43.py` — injection guard escalates
- `tests/test_guardrails_ps17.py` — tool failure / conflict guardrails
- `tests/test_output_schema_ps42.py` — strict output envelopes
- `tests/test_behavior_metrics_ps46.py` — behavior metrics emission

Restricted actions (`safe=false`) require **OPA allow** before `approval_store_create` (HITL). Deny or OPA down → escalation, no execution.

---

## Deterministic gate ordering

CI runs jobs in parallel where possible; **logical order** for developers:

1. `make check` (lint + typecheck + golden) — no Postgres  
2. `make safety-gates` — safety pytest bundle  
3. `make test` — Postgres + full pytest  
4. Eval hard gates (needs `OPENAI_API_KEY`, OPA + Telemetry MCP in CI)  
5. Eval soft signal (informational)

Final job **`gate-summary`** aggregates results, writes `ci-gate-summary.md` artifact and GitHub Step Summary.

---

## When a gate fails

| Failed gate | Likely cause | Recovery |
|-------------|--------------|----------|
| `lint-ruff` / `lint-mypy` | Code style/types | `ruff check .`, `make typecheck` |
| `golden-baseline` | Replay field drift | `make golden-check`; intentional update via `make golden-update` + confirm |
| `safety-opa-hitl` | OPA/HITL/guard regression | Run `make safety-gates`; read failing test name |
| `pytest-full` | Unit/API/DB test | `make test` with local Postgres |
| `eval-must-escalate` | Agent did not escalate | `check_escalation` / investigate evidence path |
| `eval-citation-present` | No citations / wrong escalation | Telemetry MCP + `citation-present` case |
| `eval-injection-suite` | Unsafe phrase or tool in plan | `prompt_injection.py`, plan allowlist |
| `evals-full-suite` (soft) | MoE drift on full cases | Fix agent or update `evals/cases.yaml`; **does not block merge** |
| `docker-build` | Compose/Dockerfile | `make compose-config`, `make docker-build` |

CI log format for eval hard gates: `FAIL  <case_id>  <reason>`.

---

## Emergency release override

Use only when a **hard** gate fails for a known-safe reason (infra flake, secret rotation) and risk is accepted.

1. Document in PR: gate ID, failure link, why safe to proceed, follow-up issue.  
2. Required approvals: **tech lead + on-call** (or repo owner).  
3. Prefer re-run failed job over bypass.  
4. Do **not** disable `safety-opa-hitl` or `eval-injection-suite` without security review.  
5. After merge: fix root cause and remove any temporary waiver in the same sprint.

Soft gate (`evals-soft`) failures never require override — they are informational.

---

## Local commands

```bash
# Fast hard gates (no LLM / Postgres)
make check
make safety-gates

# Single safety gate via runner
python scripts/ci_gate_runner.py --gate safety-opa-hitl

# PS1.8 hard eval gates (needs API key + MCP/OPA like CI)
python -m evals.scoring --case-id must-escalate-no-evidence
python -m evals.scoring --case-id citation-present
python -m evals.scoring --injection-only

# Soft full suite (exit 0 even on failures)
python -m evals.scoring --soft-signal
```

---

## Related docs

- [evals/README.md](../../evals/README.md) — PS1.8 deterministic gates  
- [docs/golden_run_baselines.md](../golden_run_baselines.md) — golden-check  
- [docs/prompt_injection_threat_model.md](../prompt_injection_threat_model.md) — injection hard gate
