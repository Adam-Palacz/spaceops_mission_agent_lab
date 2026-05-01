# Production Scale — Sprint 4 (PS4)

**Goal:** move to serious-mode safety and quality gates: stronger evidence policy, stricter schema
enforcement, injection hardening, golden runs, and measurable behavior metrics.

---

## Outcomes

- Expanded guardrails around evidence grounding and escalation triggers.
- CI eval suite catches citation/evidence/audit semantics regressions.
- Golden runs and behavioral metrics become release readiness inputs.
- Tool failure visibility improves (distinguish `empty` vs `error` vs policy-deny paths).

---

## Tasks

See **[BOARD.md](BOARD.md)** for status of PS4.1-PS4.8.

---

## Definition of done (sprint)

- [ ] CI fails on evidence/citation regressions with clear diagnostics.
- [ ] Tool failure outcomes are explicit in audit and metrics.
- [ ] Golden-run suite can be re-executed and compared across revisions.
- [ ] Escalation-rate/evidence-coverage/p95-stage metrics are available.
