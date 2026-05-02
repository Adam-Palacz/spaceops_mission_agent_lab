# Production Scale — Sprint 1 (PS1)

**Goal:** establish production-grade operational foundations on top of MVP:
data contracts, auditable schema evolution, replay baseline, and strict core CI gates.

---

## Outcomes

- Versioned data contracts (`TelemetryEvent`, `Incident`, `AgentReport`, `EscalationPacket`) with schema export.
- Database migrations workflow (Alembic or equivalent) and append-only/auditable tables aligned to contracts.
- Replay baseline that can re-run the same input set and compare classification/escalation outputs.
- CI blocks regressions in critical behaviors (must-escalate + evidence/citation expectations).
- Distributed tracing hardening: W3C context propagation and semantic spans across Agent -> MCP services.

---

## Tasks

See **[BOARD.md](BOARD.md)** for status of PS1.1-PS1.9.

---

## Definition of done (sprint)

- [x] Contracts v1 exist and are validated in tests.
- [x] Migrations are repeatable and documented (CI smoke: `alembic upgrade/downgrade/upgrade`).
- [x] Replay baseline is runnable and deterministic enough for regression checks.
- [x] CI includes at least one e2e must-escalate and one evidence-required gate (`evals.scoring` in `.github/workflows/ci.yml`).
- [ ] Two demo scenarios still work end-to-end after changes (manual / release smoke; see [SPRINT_REVIEW.md](SPRINT_REVIEW.md)).

**Sprint retrospective:** [SPRINT_REVIEW.md](SPRINT_REVIEW.md)
