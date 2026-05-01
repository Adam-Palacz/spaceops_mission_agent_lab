# Phase: Hardening (Phase 4)

Post–Sprint 2: documentation, runbooks, expanded evals, optional UI. Backlog; no fixed sprint boundary. See [../roadmap_F1.md](../roadmap_F1.md).

---

## Contents

- **BOARD.md** — Status of hardening tasks (backlog).
- **HARDENING-REVIEW.md** — Phase close review summary (scope, outcomes, DoD).
- **`P4.x-name.md`** — One file per hardening task (docs, runbooks, reranker, UI, evals, post-incident loop).

## Recurring (P4.7)

After each significant closed incident:

1. Add/update postmortem in `kb/postmortems/` (use `_template.md`).
2. Re-index KB: `python -m scripts.reindex_kb`.
3. Add at least one eval case (`docs/runbooks/add_eval_case.md`).
4. Run `python -m evals.scoring` and push so CI validates.

---

## Instructions for AI

- Hardening tasks can be done in any order unless a task file states a dependency.
- When implementing a P4 task, read its .md file first; update BOARD.md when starting and when done.
- Do not remove or rename tasks in BOARD without updating or removing the corresponding task .md file.
