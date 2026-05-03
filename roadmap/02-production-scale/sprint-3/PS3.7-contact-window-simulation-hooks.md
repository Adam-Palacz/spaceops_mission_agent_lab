# PS3.7 — Contact-window simulation hooks

| Field | Value |
|-------|-------|
| **Task ID** | PS3.7 |
| **Status** | Todo |

---

## Description

Introduce hooks to simulate **intermittent downlink / contact windows**: telemetry arrives in bursts tied to
simulated visibility periods; buffering + replay aligns with parent roadmap **Phase 2 space-like simulation**.

---

## Requirements

- [ ] Configuration model for ON/OFF windows (cron-like schedule or explicit intervals in tests).
- [ ] Worker or ingest respects “no contact” periods — drops or queues per documented semantics.
- [ ] Buffered telemetry **replay** when contact restores ties into PS3.4 patterns where applicable.
- [ ] Runbook bullets for operators (pointer acceptable if PS3.8 owns consolidated recovery doc).

---

## Checklist

- [ ] Avoid blocking MVP paths: feature-flag or test-only driver acceptable.

---

## Test / acceptance

- [ ] Automated test proving buffered events flush after window opens without duplication.

---

## Dependencies

- **PS3.2**–**PS3.4** foundations recommended before deep coupling.
