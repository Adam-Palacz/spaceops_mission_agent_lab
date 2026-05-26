# Production Scale — Sprint 4 (PS4)

**Goal:** move to serious-mode safety and quality gates: stronger evidence policy, stricter schema
enforcement, injection hardening, golden runs, and measurable behavior metrics — including **OPA
fail-closed + approval (HITL) integration tests** so restricted actions never slip without policy
and human gates.

---

## Outcomes

- Expanded guardrails around evidence grounding and escalation triggers.
- CI eval suite catches citation/evidence/audit semantics regressions.
- Golden runs and behavioral metrics become release readiness inputs.
- Tool failure visibility improves (distinguish `empty` vs `error` vs policy-deny paths).
- **Integration tests** (or equivalent) for **OPA deny/timeout** and **approval API** on paths that
  touch GitOps / restricted actions — default **deny** when ambiguous (ties S2.4 / S2.5).
- **Optional** hooks for **LLM-as-judge / LangSmith / RAGAS-style** gates where strict string
  equality is insufficient (parent Phase 4); PS4.4 / PS4.7 own the CI policy decision.

---

## Tasks

See **[BOARD.md](BOARD.md)** for status of PS4.1–PS4.8 (plus PS4.1.1 DX).  
**Retrospective:** [SPRINT_REVIEW.md](SPRINT_REVIEW.md).

| Task | Spec |
|------|------|
| PS4.1 | [Evidence policy enforcement](PS4.1-evidence-policy-enforcement.md) |
| PS4.1.1 | [Makefile / CI parity for local checks](PS4.1.1-makefile-ci-parity.md) |
| PS4.2 | [Strict output schema validation](PS4.2-strict-output-schema-validation.md) |
| PS4.3 | [Prompt injection hardening](PS4.3-prompt-injection-hardening.md) |
| PS4.4 | [Evals citation/audit expansion](PS4.4-evals-citation-audit-expansion.md) |
| PS4.5 | [Golden runner snapshot/diff](PS4.5-golden-runner-snapshot-diff.md) |
| PS4.6 | [Behavior metrics emission](PS4.6-behavior-metrics-emission.md) |
| PS4.7 | [CI gating policy](PS4.7-ci-gating-policy-safety-quality.md) |
| PS4.8 | [Guardrails/quality runbook update](PS4.8-guardrails-quality-runbook-update.md) |

---

## Definition of done (sprint)

- [x] CI fails on evidence/citation regressions with clear diagnostics (`evals-hard`, PS4.7).
- [x] Tool failure outcomes are explicit in audit and metrics (`agent_tool_outcome_total`, PS4.6).
- [x] Golden-run suite can be re-executed and compared across revisions (PS4.5, `make golden-check`).
- [x] Escalation-rate/evidence-coverage/p95-stage metrics are available (PS4.6, Grafana).
- [x] **OPA + approvals:** automated fail-closed + HITL path (`safety-gates`, `test_act_opa_policy`).
- [x] **PS4.4:** deterministic semantic evals (`make semantic-check`, CI `semantic-evals`).
- [x] **PS4.1 evidence policy:** model-supplied grounding only (`fill_grounding=False`); see [SPRINT_REVIEW.md](SPRINT_REVIEW.md).

**Sprint review:** [SPRINT_REVIEW.md](SPRINT_REVIEW.md) (2026-05-19, updated after audit).

---

## Upstream / downstream

- **PS3.10** proves MCP failure modes; **PS4** proves policy and audit semantics on top.
- Indexed in [phase README — Cross-cutting](../README.md#cross-cutting-durability-safety-and-evals).
