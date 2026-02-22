# Roadmap — SpaceOps Mission Agent Lab

This folder holds the **execution plan**: phases, sprints, and task-level specs. Use it to implement work in order and track status. Canonical high-level plan: [../roadmap_F1.md](../roadmap_F1.md).

---

## Structure

| Path | Content |
|------|---------|
| **[01-core/](01-core/)** | Phase: core pipeline (Sprint 1 + Sprint 2). Ingest → Report → Act + OPA + approvals. |
| **[02-hardening/](02-hardening/)** | Phase 4: docs, runbooks, expanded evals, optional UI. |

Each phase contains **sprint folders** (e.g. `01-core/sprint-1/`). Inside each sprint:

- **README.md** — Sprint goal, outcomes, and how to work in this folder.
- **BOARD.md** — Status of all tasks (Todo | In progress | Done | Blocked).
- **`Sx.y-short-name.md`** — One file per task: description, requirements, checklist, test requirements.

---

## How to use (implementation)

1. **Pick a task** — Open the sprint’s `BOARD.md`, choose a task in Todo.
2. **Open the task file** — e.g. `sprint-1/S1.1-directory-structure.md`; read Description, Requirements, Checklist.
3. **Implement** — Follow the checklist; run tests from “Test requirements”.
4. **Update BOARD.md** — Set task to In progress, then Done when complete; link PR or commit if useful.
5. **Sprint done** — When all tasks in the sprint BOARD are Done, run “Definition of done” from the sprint README.

---

## Maintenance

| Field | Value |
|-------|--------|
| **Version** | 1.0 |
| **Last updated** | 2025-02-14 |

### Instructions for AI

1. **Task work** — When implementing a task, read the task’s .md file in the sprint folder (e.g. `01-core/sprint-1/S1.4-fastapi-ingest.md`). Use its Requirements and Checklist; do not invent new scope. After implementation, suggest updating BOARD.md (e.g. task → Done).
2. **Adding tasks** — New tasks go in the right sprint folder. Create a new `Sx.y-name.md` (same format as existing tasks) and add a row to that sprint’s `BOARD.md`. Keep sprint README and BOARD in sync.
3. **Scope** — If the user asks for something that isn’t in a task file, map it to an existing task or propose a new task file and BOARD update. Do not change scope in `roadmap_F1.md` without the user’s approval.
4. **Order** — Prefer implementing tasks in sprint order (S1.1 → S1.13, then S2.1 → S2.10); respect dependencies noted in task files.
