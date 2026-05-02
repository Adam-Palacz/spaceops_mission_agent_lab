# PS2.1 — Incident list + filters (ops triage)

| Field | Value |
|-------|-------|
| **Task ID** | PS2.1 |
| **Status** | Done |

---

## Description

Ship an **incident-oriented list** in the operational UI (`apps/ui`) so operators can narrow down work by
time range, subsystem, risk, status, and confidence (and `sat_id` / `incident_id` when present in data).
List entries link to incident detail (PS2.2).

---

## Requirements

- [x] Incident list page/route with sortable or sensible default ordering (e.g. newest first).
- [x] Filters: **time window**, **subsystem**, **risk**, **status**, **confidence** (and **sat_id** if field exists on incidents).
- [x] List uses API contract(s) already exposed by `apps/api` (extend API only if necessary; prefer existing `/runs` or incidents endpoints).
- [x] Empty state and loading/error states are explicit (no silent failure).
- [x] Non-goals: no commanding controls, no decorative-only charts.

---

## Checklist

- [x] Confirm data source: files under `data/incidents/` vs Postgres; align UI with API truth.
- [x] Wire `NEXT_PUBLIC_API_BASE_URL` (see `apps/ui/.env.example`).
- [x] Accessibility basics: labels on filters, keyboard focus on list items.
- [x] Document how to run UI locally + against docker-compose API in `apps/ui/README.md`.

---

## Implementation notes (for maintainers)

- **API:** `GET /runs` returns `subsystem`, `risk`, `escalated`, `sat_id`, `confidence` (derived unless `payload.confidence` is set). Query filters: `subsystem`, `risk`, `escalated`, `status`, `sat_id`, `confidence`, `after`, `before`, `limit`. `POST /runs` persists `subsystem`, `risk`, `escalated`, `trace_id` on success for new runs.
- **API:** `GET /runs/{run_key}` returns full run JSON (file stem = `id` from list).
- **UI:** `/incidents` list + filters; `/incidents/[runKey]` minimal JSON detail (PS2.2 replaces); `/` → `/incidents`; `/approvals` for approvals.

---

## Test / acceptance

- [x] API: `tests/test_api.py` — `test_runs_get_single_run`, `test_runs_get_filter_subsystem`, `test_runs_get_rejects_invalid_run_key`.
- [x] Manual: filters change the list predictably on fixture data (`npm run dev` → `/incidents`).
- [ ] Optional: Playwright or lightweight smoke test if repo already adopts E2E (otherwise defer).
