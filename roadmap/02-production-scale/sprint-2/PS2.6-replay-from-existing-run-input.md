# PS2.6 — Replay from existing run input

| Field | Value |
|-------|-------|
| **Task ID** | PS2.6 |
| **Status** | Todo |

---

## Description

Expose **replay from stored run metadata** in the product surface: operator triggers a **re-run** with
the same captured inputs (`run_id`, payload hash, input refs) as defined in PS1.4–PS1.5, and sees
**pass/fail vs baseline** (or diff summary).

---

## Requirements

- [ ] UI button or form: enter `run_id` → call existing replay API/CLI contract (prefer HTTP on `apps/api` if missing, add minimal endpoint).
- [ ] Display replay outcome: success, diff detected (exit semantics aligned with `apps/replay/workflow.py`).
- [ ] Auth: respect existing approval/API key patterns if replay endpoint is sensitive.

---

## Checklist

- [ ] Reuse `replay_by_run_id` / `scripts/replay_run.py` behaviour; avoid duplicating diff logic in UI.
- [ ] Document operator steps in `apps/ui/README.md` or `docs/runbooks/`.

---

## Test / acceptance

- [ ] Manual: replay a known fixture run id twice — second run compares to baseline per PS1.5 semantics.
