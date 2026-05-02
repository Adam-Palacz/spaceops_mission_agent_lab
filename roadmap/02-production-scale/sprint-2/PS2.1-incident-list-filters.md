# PS2.1 — Incident list + filters (ops triage)

| Field | Value |
|-------|-------|
| **Task ID** | PS2.1 |
| **Status** | Todo |

---

## Description

Ship an **incident-oriented list** in the operational UI (`apps/ui`) so operators can narrow down work by
time range, subsystem, risk, status, and confidence (and `sat_id` / `incident_id` when present in data).
List entries link to incident detail (PS2.2).

---

## Requirements

- [ ] Incident list page/route with sortable or sensible default ordering (e.g. newest first).
- [ ] Filters: **time window**, **subsystem**, **risk**, **status**, **confidence** (and **sat_id** if field exists on incidents).
- [ ] List uses API contract(s) already exposed by `apps/api` (extend API only if necessary; prefer existing `/runs` or incidents endpoints).
- [ ] Empty state and loading/error states are explicit (no silent failure).
- [ ] Non-goals: no commanding controls, no decorative-only charts.

---

## Checklist

- [ ] Confirm data source: files under `data/incidents/` vs Postgres; align UI with API truth.
- [ ] Wire `NEXT_PUBLIC_API_BASE_URL` (see `apps/ui/.env.example`).
- [ ] Accessibility basics: labels on filters, keyboard focus on list items.
- [ ] Document how to run UI locally + against docker-compose API in `apps/ui/README.md`.

---

## Test / acceptance

- [ ] Manual: filters change the list predictably on fixture data.
- [ ] Optional: Playwright or lightweight smoke test if repo already adopts E2E (otherwise defer).
