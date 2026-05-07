# PS3.8 — Ops runbook: queue + DLQ recovery

| Field | Value |
|-------|-------|
| **Task ID** | PS3.8 |
| **Status** | Done |

---

## Description

Single operator-facing **runbook** for queue/DLQ incidents: triage checklist, replay procedures,
rollback posture, and links to MCP breaker scenarios (**PS3.10**) where overlapping symptoms occur.

---

## Requirements

- [x] Doc under `docs/runbooks/`: `docs/runbooks/queue_dlq_recovery.md`.
- [x] Sections delivered: symptoms → diagnostics (logs/queries) → safe replay steps → escalation criteria.
- [x] Cross-links added: PS3.4 replay tooling, PS3.3 DLQ, PS3.10 MCP lossy-link overlap.

---

## Checklist

- [x] Compose-oriented commands added for health checks and Postgres diagnostics.

---

## Test / acceptance

- [x] Walkthrough-oriented section included: "Junior-friendly execution order" with sequential commands.

---

## Dependencies

- **PS3.3** DLQ shape stable enough to document queries/APIs.
