# PS2.5 — Jaeger deep links + run correlation in UI

| Field | Value |
|-------|-------|
| **Task ID** | PS2.5 |
| **Status** | Done |

---

## Description

From run/incident UI, provide a **Jaeger UI deep link** (same pattern as agent report: `jaeger_ui_url` +
trace id query) so operators jump from **SpaceOps UI → full trace** in one click.

---

## Requirements

- [x] “View trace in Jaeger” / list **View trace ↗** opens correct trace for `trace_id` / `trace_link`; run detail shows `run_id` for correlation.
- [x] Base URL configurable (`NEXT_PUBLIC_JAEGER_UI_URL` or reuse `report.trace_link` when present).
- [x] Graceful message if trace id missing (run not instrumented or pre-OTel).

---

## Checklist

- [x] Align URL format with `docs/runbooks/distributed_tracing_ps19.md` and docker-compose Jaeger port.
- [x] Do not embed Jaeger in iframe unless explicitly desired (default: new tab).

---

## Test / acceptance

- [x] Manual: link resolves to a trace for a recent `POST /runs` when collector + Jaeger are up.
