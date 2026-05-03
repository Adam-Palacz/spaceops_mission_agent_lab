# PS3.5 — Burst / backpressure load scenario

| Field | Value |
|-------|-------|
| **Task ID** | PS3.5 |
| **Status** | Todo |

---

## Description

Validate that **ingest and workers remain stable under burst load**: no crash loops, no offset corruption,
bounded memory growth. Aligns with sprint DoD: **backpressure does not crash ingest or corrupt offsets**.

---

## Requirements

- [ ] Automated scenario (pytest marker or CI job step) or scripted benchmark reproducible locally + CI optional tier.
- [ ] Metrics/assertions: ingest accepts load with bounded failures OR explicit shedding documented.
- [ ] Document thresholds (events/sec, duration) and environment assumptions (Compose vs bare metal).

---

## Checklist

- [ ] Capture baseline numbers for regression comparison (even if logged manually once).

---

## Test / acceptance

- [ ] Scenario passes on developer laptop OR documented CI profile (smaller burst if resource constrained).

---

## Dependencies

- **PS3.2** worker loop live enough to exercise under load.
