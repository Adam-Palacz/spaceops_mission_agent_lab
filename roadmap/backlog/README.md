# Backlog

**Pool of ideas and specs** for future work. The backlog **has no statuses** — it is used to **create new sprint tasks** when you schedule something.

---

## Principle

- **Backlog** = list of items (title + short description + spec file).
- When you want to do something in a sprint: **create a task in the sprint** (e.g. S1.x, S2.x, or P4.x) using the backlog spec (copy requirements, checklist, tests from `BL-xxx-*.md`).
- After scheduling an item in a sprint: you can add a note in the backlog (e.g. "→ S2.15") or leave it as-is — the backlog does not track state.

---

## Contents

- **[items.md](items.md)** — List of backlog items (title, one-line description, link to spec). No Status column.
- **`BL-xxx-short-name.md`** — Full spec (description, requirements, checklist, test requirements) in the same format as sprint tasks, so it can be moved to Sx.y easily.

---

## How to add a sprint task from the backlog

1. Open the backlog spec file (e.g. `BL-001-monitoring-improvement-analysis.md`).
2. In the target sprint folder, create a new task file: `Sx.y-name.md` (e.g. in Phase 4: `P4.8-monitoring-analysis.md`) — copy or adapt Description, Requirements, Checklist, Test requirements.
3. Add a row to that sprint’s BOARD.md (Task | Title | Status | Task file).
4. Implement and track status **in the sprint BOARD**, not in the backlog.

---

## Instructions for AI

- The backlog **has no BOARD with statuses**. The file `items.md` is just a list of items with links to specs.
- When the user plans to do something from the backlog in a sprint: create a new task file in the right sprint (or Phase 4), use the content from `BL-xxx-*.md`, add a row to that sprint’s BOARD.
- New ideas: add a row to `items.md` and create `BL-xxx-name.md` (no status to set).
