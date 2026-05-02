# PS2.3 — Run timeline + stage durations

| Field | Value |
|-------|-------|
| **Task ID** | PS2.3 |
| **Status** | Done |

---

## Description

Surface **pipeline stages** (triage → investigate → decide → act → report) with **duration / status**
per stage so operators see where time went and whether a stage failed vs skipped (e.g. escalation short-circuit).

**Source of truth:** `stage_timings` on the run JSON (written by `POST /runs` from agent state). OTel/Jaeger remains the span-level waterfall; the UI timeline does not depend on Jaeger.

---

## Requirements

- [x] Timeline UI on incident or run detail: stage name, duration, outcome (ok / error; skipped = stage absent from list).
- [x] Correlation by `run_id` (and `trace_id` if exposed by API).
- [x] If Jaeger is unavailable, UI still shows best-effort timeline from local metadata.
- [x] Avoid duplicating Jaeger’s full waterfall; keep a **compact ops timeline**.

---

## Checklist

- [x] Define minimal JSON shape returned by API (extend `apps/api` if needed).
- [x] Align stage names with LangGraph node names in `apps/agent/graph.py` for consistency.
- [x] Document fallback behaviour when spans are missing.

---

## Test / acceptance

- [x] Manual: single run shows plausible durations; failed MCP stage visible when induced in dev.
