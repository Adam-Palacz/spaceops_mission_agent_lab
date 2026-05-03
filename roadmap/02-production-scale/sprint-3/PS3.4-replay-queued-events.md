# PS3.4 — Replay tooling for queued events

| Field | Value |
|-------|-------|
| **Task ID** | PS3.4 |
| **Status** | Todo |

---

## Description

Extend replay beyond **single-run input replay** (PS1.5): support **re-driving** processing from a
**range of offsets**, a **subset of DLQ events**, or a **time window**, while preserving traceability
(`run_id`, audit correlation). Must coexist with **PS3.2** idempotency (replay must not blindly duplicate).

---

## Requirements

- [ ] CLI or documented script entrypoint (e.g. `scripts/replay_queue.py`) with filters: offset range, DLQ ids, time bounds.
- [ ] Explicit `--dry-run` or confirmation flag for destructive replay batches.
- [ ] Documentation cross-link to PS1.5 replay semantics (“replay pipeline” vs “re-consume queue”).
- [ ] Tests with mocked broker/table backend proving idempotent replay path.

---

## Checklist

- [ ] UI optional follow-up (defer unless trivial): surface DLQ replay behind internal-only route.

---

## Test / acceptance

- [ ] CI-visible test: replay subset advances offsets correctly and respects idempotency.

---

## Dependencies

- **PS3.2**, **PS3.3** operational paths stable enough to define replay contracts.
