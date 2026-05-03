# PS2.7 — Fixture upload + simulate run

| Field | Value |
|-------|-------|
| **Task ID** | PS2.7 |
| **Status** | Done |

---

## Description

Allow uploading a **small fixture** (controlled NDJSON / incident JSON) to **simulate** a run without
replacing production data paths — useful for demos, support, and regression reproduction.

---

## Requirements

- [x] File upload UI with strict size/type limits (reject arbitrary binaries / UTF-8 JSON cap 48 KiB server-side).
- [x] Server-side validation: single JSON object with `incident_id` + `payload` (incident-shaped; NDJSON → use `POST /ingest`).
- [x] Run uses synthetic **`sim-upload-<token>-<slug>`** `incident_id`, persisted **`simulation": true`**, **`source_fixture_incident_id`** — documented in `docs/runbooks/fixture_upload_simulation.md`.
- [x] Same run persistence + UI detail (report, trace, PS2.3/2.4/2.5 panels) as normal runs; list **SIM** badge + `?simulation=` filter.

---

## Checklist

- [x] Threat model: runbook table (path basename only, size cap, UTF-8/JSON, no `dangerouslySetInnerHTML`); virus scan out of scope.
- [x] Rate limit / auth: same as `POST /runs` in MVP; runbook notes gateway for non-dev.

---

## Test / acceptance

- [x] Manual: upload minimal valid fixture → run completes → appears in list with **SIM** badge / filter.
