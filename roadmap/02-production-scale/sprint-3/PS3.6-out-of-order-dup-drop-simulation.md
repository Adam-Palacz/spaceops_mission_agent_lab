# PS3.6 — Out-of-order / dup / drop simulation (telemetry stream)

| Field | Value |
|-------|-------|
| **Task ID** | PS3.6 |
| **Status** | Todo |

---

## Description

Prove robustness of **telemetry stream handling** when transport exhibits **drops**, **duplicates**, or
**out-of-order** arrival — ground IT realism without full CCSDS. Distinct from **PS3.10** (MCP HTTP transport chaos).

---

## Requirements

- [ ] Fault injector or test harness configurable probabilities/latencies for reorder/dup/drop.
- [ ] Assertions: ordering violations do not corrupt durable state; duplicates handled via PS3.2 keys.
- [ ] Sequence / validity hooks compatible with future Phase 3 adapter (document interfaces — CRC-like optional stub).

---

## Checklist

- [ ] Separate doc note vs PS3.10 scope boundary.

---

## Test / acceptance

- [ ] At least one automated disruption scenario meets sprint DoD line (“≥ one disruption scenario”).

---

## Dependencies

- **PS3.2** idempotency semantics.
