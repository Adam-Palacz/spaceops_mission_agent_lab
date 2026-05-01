# PS1.3 — DB migrations baseline + contract-aligned tables

| Field | Value |
|-------|--------|
| **Task ID** | PS1.3 |
| **Status** | Done |

---

## Description

Establish a migration-driven database baseline aligned with v1 contracts and auditability
requirements. Schema changes must be reproducible, reviewable, and reversible.

---

## Requirements

- [x] Migration toolchain exists (Alembic or equivalent).
- [x] Baseline tables exist: `telemetry_events`, `incidents`, `runs`, `audit_log`.
- [x] `audit_log` and `telemetry_events` follow append-only semantics.
- [x] Migration workflow documented (`upgrade`, `downgrade`, local reset).
- [x] CI validates migrations can apply on clean database.

---

## Checklist

- [x] Add migration config and initial revision.
- [x] Define indexes/constraints matching dedupe and lookup patterns.
- [x] Add DB-level comments or docs mapping table fields to contracts.
- [x] Add migration smoke test in CI/local test suite.
- [x] Document operational migration runbook.

---

## Test requirements

- [x] Fresh DB + migrate up works end-to-end.
- [x] Optional downgrade path works for baseline revision.
- [x] App boots and runs scenarios against migrated schema.
