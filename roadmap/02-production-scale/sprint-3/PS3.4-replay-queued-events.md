# PS3.4 — Replay tooling for queued events

| Field | Value |
|-------|-------|
| **Task ID** | PS3.4 |
| **Status** | Done |

---

## Description

Extend replay beyond **single-run input replay** (PS1.5): support **re-driving** processing from a
**range of offsets**, a **subset of DLQ events**, or a **time window**, while preserving traceability
(`run_id`, audit correlation). Must coexist with **PS3.2** idempotency (replay must not blindly duplicate).

---

## Requirements

- [x] CLI entrypoint: `scripts/replay_queue.py` with filters:
  - DLQ subset (`--dlq-ids`)
  - DLQ time window (`--after`, `--before`)
  - stream sequence range (`--seq-start`, `--seq-end`)
- [x] Explicit safe mode: dry-run is default; publish only with `--apply`.
- [x] Docs cross-link to PS1.5 semantics in `docs/runbooks/replay_workflow.md`.
- [x] Tests with mocked backend proving idempotent replay path (`tests/test_replay_queue.py`).

---

## Checklist

- [x] UI optional follow-up deferred (no UI change in this task).

---

## Test / acceptance

- [x] CI-visible test: `tests/test_replay_queue.py` verifies subset replay planning + local
      dedupe by `event_id` before publish.

---

## Delivered

- Module: `apps/replay/queue_replay.py`
  - DLQ selection by IDs / time bounds
  - item normalization and idempotent dedupe (`event_id`)
- Script: `scripts/replay_queue.py`
  - dry-run summary by default
  - publish path via `--apply`
  - supports DLQ and stream sequence replay
- Docs: `docs/runbooks/replay_workflow.md` queue replay section.

---

## Dependencies

- **PS3.2**, **PS3.3** operational paths stable enough to define replay contracts.
