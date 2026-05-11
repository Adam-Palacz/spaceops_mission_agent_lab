# PS4.1.1 — Makefile: local DX and CI parity

| Field | Value |
|-------|-------|
| **Task ID** | PS4.1.1 |
| **Status** | Done |
| **Related** | PS4.1 (evidence policy); PS4.7 (CI gating policy) |

---

## Description

Provide a single entry point (`make help`) for common quality gates aligned with `.github/workflows/ci.yml`,
so contributors can run the same checks locally before push (POSIX Make; Git Bash / WSL on Windows).

---

## Requirements

- [x] Documented targets: install, lint, typecheck, format, golden-check, test (with DB env), migrate-smoke, compose sanity, docker build profile matching CI.
- [x] `check` (or equivalent) runs fast gates without Postgres: lint + typecheck + golden-check.
- [x] Variables for `PYTHON`, compose file path, and optional `DATABASE_URL` defaults matching local dev docs.

---

## Checklist

- [x] `Makefile` updated with `.PHONY`, `help`, and CI-aligned recipes.
- [x] Sprint board / README reference this task.

---

## Test / acceptance

- [x] `make help` lists all targets with short descriptions.
- [x] `make check` succeeds in a clean venv with deps installed (no DB required for this target).

Implemented artifacts:

- `Makefile` (targets + comments)
- This spec + `BOARD.md` / `README.md` (sprint 4)
