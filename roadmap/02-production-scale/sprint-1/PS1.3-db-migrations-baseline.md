# PS1.3 — DB migrations baseline + contract-aligned tables

| Field | Value |
|-------|--------|
| **Task ID** | PS1.3 |
| **Status** | Todo |

---

## Description

Establish a migration-driven database baseline aligned with v1 contracts and auditability
requirements. Schema changes must be reproducible, reviewable, and reversible.

---

## Requirements

- [ ] Migration toolchain exists (Alembic or equivalent).
- [ ] Baseline tables exist: `telemetry_events`, `incidents`, `runs`, `audit_log`.
- [ ] `audit_log` and `telemetry_events` follow append-only semantics.
- [ ] Migration workflow documented (`upgrade`, `downgrade`, local reset).
- [ ] CI validates migrations can apply on clean database.

---

## Checklist

- [ ] Add migration config and initial revision.
- [ ] Define indexes/constraints matching dedupe and lookup patterns.
- [ ] Add DB-level comments or docs mapping table fields to contracts.
- [ ] Add migration smoke test in CI/local test suite.
- [ ] Document operational migration runbook.

---

## Test requirements

- [ ] Fresh DB + migrate up works end-to-end.
- [ ] Optional downgrade path works for baseline revision.
- [ ] App boots and runs scenarios against migrated schema.
