# PS2.4 — Escalation packet UI

| Field | Value |
|-------|-------|
| **Task ID** | PS2.4 |
| **Status** | Todo |

---

## Description

When `escalated` is true, show **`EscalationPacket`** fields explicitly: **reason**, **what we know**,
**what we don’t know**, **what to check next** — so reviewers can validate escalation without reading raw JSON.

---

## Requirements

- [ ] Escalation panel visible only when escalation data exists; non-escalated runs hide or collapse it.
- [ ] Render lists (`what_we_know`, etc.) as readable bullets; empty lists handled.
- [ ] Optional: show `escalation_reason` tag line if separate from packet (align with tracing low-card tags).

---

## Checklist

- [ ] Confirm API returns `escalation_packet` (or equivalent) on run/incident payloads.
- [ ] Match contract `EscalationPacket` / schema from PS1.1 where applicable.

---

## Test / acceptance

- [ ] Manual: incident with `must_escalate` eval path shows populated packet; non-escalated incident does not mislead.
