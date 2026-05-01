# PS1.4 — Replay metadata capture

| Field | Value |
|-------|--------|
| **Task ID** | PS1.4 |
| **Status** | Done |

---

## Description

Capture enough metadata per run to replay inputs deterministically and compare outcomes across
code/model revisions. This is the foundation for golden runs and regression triage.

---

## Requirements

- [x] Persist replay metadata for each run (`run_id`, payload hash, input refs/event IDs).
- [x] Persist model/prompt/runtime metadata required for reproducibility.
- [x] Replay metadata links to audit and trace IDs.
- [x] Capture is automatic for API and eval-triggered runs.
- [x] Metadata schema is documented and versioned.

---

## Checklist

- [x] Define replay metadata structure.
- [x] Add write path during run creation/completion.
- [x] Add read API/helper for replay retrieval by `run_id`.
- [x] Extend docs with replay assumptions and known non-determinism.
- [x] Add tests for metadata presence/completeness.

---

## Test requirements

- [x] Every new run has persisted replay metadata.
- [x] Metadata can be fetched and reused to trigger replay.
- [x] Missing/partial metadata is handled with clear errors.
