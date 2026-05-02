# PS2.5 — Jaeger deep links + run correlation in UI

| Field | Value |
|-------|-------|
| **Task ID** | PS2.5 |
| **Status** | Todo |

---

## Description

From run/incident UI, provide a **Jaeger UI deep link** (same pattern as agent report: `jaeger_ui_url` +
trace id query) so operators jump from **SpaceOps UI → full trace** in one click.

---

## Requirements

- [ ] “View trace in Jaeger” (or icon) opens correct trace for `trace_id` / `run_id` mapping used in repo.
- [ ] Base URL configurable (`NEXT_PUBLIC_JAEGER_UI_URL` or reuse API-provided link field if already present).
- [ ] Graceful message if trace id missing (run not instrumented or pre-OTel).

---

## Checklist

- [ ] Align URL format with `docs/runbooks/distributed_tracing_ps19.md` and docker-compose Jaeger port.
- [ ] Do not embed Jaeger in iframe unless explicitly desired (default: new tab).

---

## Test / acceptance

- [ ] Manual: link resolves to a trace for a recent `POST /runs` when collector + Jaeger are up.
