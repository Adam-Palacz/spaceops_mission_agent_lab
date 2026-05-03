# PS2 — Sprint review

**Sprint:** Production Scale — Sprint 2 (PS2.1–PS2.8)  
**Board:** [BOARD.md](BOARD.md) — all tasks **Done**  
**Date:** 2026-05-03 (review)

---

## Executive summary

PS2 delivered a **thin operational UI** on top of PS1 foundations: incident triage (list/detail), **evidence and timeline**, **escalation packet** visibility, **Jaeger correlation** from runs, **replay** from stored inputs (API + UI + CLI alignment), **fixture simulate** flows, and **golden-run baselines** with CI-backed regression checks. The sprint goal from [README.md](README.md) is met for ops-oriented diagnosis and reproducibility; deeper product polish and full **automated E2E “scenario A/B”** in CI remain optional hardening for a later sprint.

---

## Goals vs outcomes

| README outcome | Status |
|----------------|--------|
| Incident-oriented UI flow (list/detail/evidence/timeline/escalation/trace) | Done (PS2.1–PS2.5); SpaceOps UI under `apps/ui/` |
| Replay entry points from UI/CLI on known fixtures | Done (PS2.6); see `docs/runbooks/replay_workflow.md`, `/replays`, `scripts/replay_run.py` |
| Fixture upload + simulate path | Done (PS2.7); API + `/simulate`, runbook `docs/runbooks/fixture_upload_simulation.md` |
| Golden-run snapshots + baseline comparison in engineering workflow | Done (PS2.8); `docs/golden_run_baselines.md`, `tests/test_golden_baseline.py`, `scripts/golden_baseline.py`, `make golden-check` |
| Documentation for external reviewer walkthrough | Done via runbooks + UI README + golden/replay docs (no single “tour” page required by board) |

---

## Definition of Done (sprint checklist)

Aligned with [README.md](README.md); evidence is repo-local (paths / CI).

1. **Reviewer can diagnose scenario A/B using UI evidence + trace links** — Supported by incident detail (evidence panel, timeline/stage durations where implemented), escalation packet UI, and Jaeger deep links (PS2.3–PS2.5). Validation is **manual / staging walkthrough**, not a dedicated CI Playwright job.
2. **Replay from stored inputs and fixture uploads documented and executable** — Runbooks + replay API/UI + simulate endpoints (PS2.6–PS2.7).
3. **Golden-run diff workflow in CI or documented gate** — `pytest tests/test_golden_baseline.py` in `.github/workflows/ci.yml` `test` job; optional real pins under `data/replay/golden/` with `scripts/golden_baseline.py check`.
4. **UI stays decision-support focused** — Scope stayed ops-facing (incidents, runs, replay, simulate); no broad product expansion tracked on PS2 board.

---

## What shipped (by theme)

- **Ops UI:** incident list/filters, detail + evidence, run timeline / stage durations (PS2.1–PS2.3).
- **Escalation transparency:** escalation packet surfaced in UI (PS2.4).
- **Observability links:** Jaeger/trace correlation from run-oriented views (PS2.5).
- **Reproducibility:** replay from `run_id`, artifact resolution by `payload_hash` / `incident_*.json`, UI + API parity with workflow (PS2.6).
- **Simulation:** quick form + multipart fixture upload, API list filter for simulation runs (PS2.7).
- **Regression discipline:** extended replay comparison fields (`escalation_reason`, `citation_count`), golden manifest + baseline schema, Makefile targets (PS2.8).
- **CI / Docker:** image build job and root `.dockerignore` to keep compose builds tractable (supporting PS2 UI delivery).

---

## Operational lessons (same timeframe as PS2 close-out)

These were **not always separate board tasks** but affected delivery of the UI + Compose path:

| Topic | Lesson |
|-------|--------|
| **Next.js build in Docker** | Strict TypeScript on `simulate` page (type predicates / select `onChange`) must pass `npm run build`; catch early with local `npx tsc --noEmit` or CI `docker-build` job. |
| **Compose build context** | Root `Dockerfile` contexts were huge without a root `.dockerignore`; trimming `data/`, caches, and tests speeds CI and local `docker compose build`. |
| **Golden vs live LLM** | CI golden check uses a **synthetic fixture** + mocked pipeline so PRs do not depend on `OPENAI_API_KEY`; real `run_id` pins stay optional under `data/replay/golden/`. |

---

## Risks and carryover

| Risk | Mitigation |
|------|------------|
| Replay / golden **flakiness** when real models or MCP data drift | Keep temperature=0 where applicable; refresh baselines and eval cases intentionally; document in `docs/golden_run_baselines.md`. |
| **Scenario A/B not in CI** as full browser E2E | Optional next sprint: Playwright smoke against compose, or scripted API+UI checklist in runbook. |
| **evals** job still depends on secrets for full scoring | Unchanged from PS1; keep fork/PR policy for external contributors. |
| **PS4.5** “golden runner depth” (per README index) | PS2.8 provides baseline + docs; deeper runner product can extend manifest and reporting without redoing schema. |

---

## Recommendation

**Close PS2** from a planning perspective: board is green, UI and replay/golden workflows are integrated and documented. **Next:** pick PS3 (or adjacent phase) priorities—e.g. automated E2E smoke, richer trace/span naming for Jaeger “pipeline view”, or PS4.5 golden runner—without blocking on re-opening PS2 scope.

---

## Actions captured in repo

- [README.md](README.md) — Definition of Done checkboxes updated for sprint sign-off.
- This file — single place for retrospective and sign-off.
