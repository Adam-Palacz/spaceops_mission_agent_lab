# PS4 — Sprint review

**Sprint:** Production Scale — Sprint 4 (PS4.1–PS4.8)  
**Board:** [BOARD.md](BOARD.md) — **8 / 8 Done**  
**Date:** 2026-05-19 (review; PS4.4 + audit fixes 2026-05-19)

---

## Executive summary

PS4 delivered **serious-mode safety and quality**: evidence policy (with grounding fix), strict schemas, prompt-injection guards, golden replay diff, behavior metrics (incl. per-tool outcomes), hard/soft CI gates, operator triage runbook, and **deterministic semantic evals (PS4.4)** that run without `OPENAI_API_KEY`.

Sprint goal from [README.md](README.md) is **met**. Live LLM evals remain optional on forks (skipped when secret missing); **semantic-evals** + **safety-gates** protect citation/audit semantics on every PR.

---

## Goals vs outcomes

| README outcome | Status |
|----------------|--------|
| Expanded guardrails around evidence grounding | Done (PS4.1 + `fill_grounding=False`, act/report checks) |
| CI eval suite catches citation/evidence/audit semantics | Done (PS4.4 semantic fixtures + PS1.8 live gates when key set) |
| Golden runs + behavioral metrics | Done (PS4.5, PS4.6) |
| Tool failure visibility in audit and metrics | Done (`tool_outcomes`, `agent_tool_outcome_total`) |
| OPA fail-closed + HITL tests | Done (PS4.7 `safety-gates`) |

---

## Board summary

| Task | Status |
|------|--------|
| PS4.1 – PS4.3, PS4.5 – PS4.8 | Done |
| PS4.4 Semantic eval expansion | Done |

---

## Definition of Done (sprint checklist)

1. **CI fails on evidence/citation regressions** — `semantic-evals`, `safety-gates`, live `evals-hard` (with key).
2. **Tool outcomes in audit and metrics** — `agent_tool_outcome_total`.
3. **Golden replay comparable** — PS4.5.
4. **Behavior metrics** — PS4.6.
5. **OPA + HITL proof** — PS4.7.
6. **PS4.4 deterministic subset** — `python -m evals.semantic`, CI artifact.

---

## What shipped (by theme)

- **PS4.1** — Evidence policy; no synthetic grounding before validation.
- **PS4.2** — Output schema fail-closed.
- **PS4.3** — Prompt injection guard.
- **PS4.4** — `evals/semantic_cases.yaml`, 7 fixtures, `evals/semantic.py`, CI `semantic-evals`.
- **PS4.5** — Golden runner.
- **PS4.6** — Behavior + tool outcome metrics.
- **PS4.7** — CI gate matrix; eval skip without API key.
- **PS4.8** — [guardrails_quality_triage.md](../../../docs/runbooks/guardrails_quality_triage.md).

---

## CI architecture

```text
lint → golden-check → safety-gates → semantic-evals → test → docker-build
                              ↓
                    evals-hard (live, if OPENAI_API_KEY)
                              ↓
                    evals-soft (soft signal, if key)
                              ↓
                    gate-summary
```

---

## Recommendation

**Close PS4** for planning and delivery. Next: PS5 / cluster per phase README, or expand live eval cases using the same rubric fields as semantic suite.

---

## Actions captured in repo

- [README.md](README.md) — DoD complete  
- [SPRINT_REVIEW.md](SPRINT_REVIEW.md) — this file  
- [PS4.4 spec](PS4.4-evals-citation-audit-expansion.md) — Done  
