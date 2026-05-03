# PS3.8 — Ops runbook: queue + DLQ recovery

| Field | Value |
|-------|-------|
| **Task ID** | PS3.8 |
| **Status** | Todo |

---

## Description

Single operator-facing **runbook** for queue/DLQ incidents: triage checklist, replay procedures,
rollback posture, and links to MCP breaker scenarios (**PS3.10**) where overlapping symptoms occur.

---

## Requirements

- [ ] Doc under `docs/runbooks/` (e.g. `queue_dlq_recovery.md`).
- [ ] Sections: symptoms → diagnostics (metrics/logs/queries) → safe replay steps → escalation criteria.
- [ ] Cross-links: PS3.4 replay tooling, PS3.3 DLQ schema, PS3.10 MCP storm bullets.

---

## Checklist

- [ ] Compose-oriented commands (`docker compose … exec …`) where relevant.

---

## Test / acceptance

- [ ] Tech reviewer walkthrough: junior engineer can execute recovery steps without reading source.

---

## Dependencies

- **PS3.3** DLQ shape stable enough to document queries/APIs.
