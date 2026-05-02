# PS2.4 — Escalation packet UI

| Field | Value |
|-------|-------|
| **Task ID** | PS2.4 |
| **Status** | Done |

---

## Description

When `escalated` is true, show **`EscalationPacket`** fields explicitly: **reason**, **what we know**,
**what we don’t know**, **what to check next** — so reviewers can validate escalation without reading raw JSON.

---

## Requirements

- [x] Escalation panel visible only when escalation data exists; non-escalated runs hide or collapse it.
- [x] Render lists (`what_we_know`, etc.) as readable bullets; empty lists handled.
- [x] Optional: show `escalation_reason` tag line if separate from packet (align with tracing low-card tags).

---

## Checklist

- [x] Confirm API returns `escalation_packet` (or equivalent) on run/incident payloads (`report.escalation_packet` on `GET /runs/{run_key}`).
- [x] Match contract `EscalationPacket` / schema from PS1.1 where applicable (`reason`, `what_we_know`, `what_we_dont_know`, `what_to_check`).

---

## Test / acceptance

- [x] Manual: incident with `must_escalate` eval path shows populated packet; non-escalated incident does not mislead.
