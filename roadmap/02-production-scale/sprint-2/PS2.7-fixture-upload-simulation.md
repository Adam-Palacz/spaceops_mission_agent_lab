# PS2.7 — Fixture upload + simulate run

| Field | Value |
|-------|-------|
| **Task ID** | PS2.7 |
| **Status** | Todo |

---

## Description

Allow uploading a **small fixture** (controlled NDJSON / incident JSON) to **simulate** a run without
replacing production data paths — useful for demos, support, and regression reproduction.

---

## Requirements

- [ ] File upload UI with strict size/type limits (reject arbitrary binaries).
- [ ] Server-side validation using same ingest / incident validation as normal pipeline where possible.
- [ ] Run triggered in **isolated** or clearly labelled mode (e.g. prefixed `incident_id` or sandbox flag) so operators do not confuse with production incidents — document behaviour.
- [ ] Show resulting report + evidence + trace link like a normal run.

---

## Checklist

- [ ] Threat model: no path traversal, no SSR from uploaded content; virus scan out of scope but mention.
- [ ] Rate limit or auth requirement if exposed beyond local dev.

---

## Test / acceptance

- [ ] Manual: upload minimal valid fixture → run completes → appears in list with distinct label.
