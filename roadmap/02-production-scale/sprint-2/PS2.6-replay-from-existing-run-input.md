# PS2.6 — Replay from existing run input

| Field | Value |
|-------|-------|
| **Task ID** | PS2.6 |
| **Status** | Done |

---

## Description

Expose **replay from stored run metadata** in the product surface: operator triggers a **re-run** with
the same captured inputs (`run_id`, payload hash, input refs) as defined in PS1.4–PS1.5, and sees
**pass/fail vs baseline** (or diff summary).

---

## Requirements

- [x] UI form: `/replays` + run detail **Run replay & compare** → existing `GET/POST /replays/{run_id}` (no new endpoint).
- [x] Display replay outcome: `comparison.has_diff` + diffs table (aligned with `apps/replay/workflow.py` / CLI `0` vs `2`).
- [x] Auth: replay endpoints unchanged (same exposure as `POST /runs`; approvals still use API key only).

---

## Checklist

- [x] Reuse `replay_by_run_id` / `scripts/replay_run.py` behaviour; UI only renders API `comparison` payload.
- [x] Document operator steps in `apps/ui/README.md` and `docs/runbooks/replay_workflow.md`.

---

## Test / acceptance

- [x] Manual: replay a known fixture run id twice — second run compares to baseline per PS1.5 semantics.
