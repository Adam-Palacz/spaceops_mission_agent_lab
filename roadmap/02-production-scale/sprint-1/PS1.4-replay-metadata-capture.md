# PS1.4 — Replay metadata capture

| Field | Value |
|-------|--------|
| **Task ID** | PS1.4 |
| **Status** | Todo |

---

## Description

Capture enough metadata per run to replay inputs deterministically and compare outcomes across
code/model revisions. This is the foundation for golden runs and regression triage.

---

## Requirements

- [ ] Persist replay metadata for each run (`run_id`, payload hash, input refs/event IDs).
- [ ] Persist model/prompt/runtime metadata required for reproducibility.
- [ ] Replay metadata links to audit and trace IDs.
- [ ] Capture is automatic for API and eval-triggered runs.
- [ ] Metadata schema is documented and versioned.

---

## Checklist

- [ ] Define replay metadata structure.
- [ ] Add write path during run creation/completion.
- [ ] Add read API/helper for replay retrieval by `run_id`.
- [ ] Extend docs with replay assumptions and known non-determinism.
- [ ] Add tests for metadata presence/completeness.

---

## Test requirements

- [ ] Every new run has persisted replay metadata.
- [ ] Metadata can be fetched and reused to trigger replay.
- [ ] Missing/partial metadata is handled with clear errors.
