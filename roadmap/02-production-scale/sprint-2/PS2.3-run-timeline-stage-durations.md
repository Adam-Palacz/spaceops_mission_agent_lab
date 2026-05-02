# PS2.3 — Run timeline + stage durations

| Field | Value |
|-------|-------|
| **Task ID** | PS2.3 |
| **Status** | Todo |

---

## Description

Surface **pipeline stages** (triage → investigate → decide → act → report) with **duration / status**
per stage so operators see where time went and whether a stage failed vs skipped (e.g. escalation short-circuit).

Data may come from **OTel spans**, persisted run metadata, or API-composed view — pick one source of truth and document it.

---

## Requirements

- [ ] Timeline UI on incident or run detail: stage name, duration, outcome (ok / error / skipped).
- [ ] Correlation by `run_id` (and `trace_id` if exposed by API).
- [ ] If Jaeger is unavailable, UI still shows best-effort timeline from local metadata.
- [ ] Avoid duplicating Jaeger’s full waterfall; keep a **compact ops timeline**.

---

## Checklist

- [ ] Define minimal JSON shape returned by API (extend `apps/api` if needed).
- [ ] Align stage names with LangGraph node names in `apps/agent/graph.py` for consistency.
- [ ] Document fallback behaviour when spans are missing.

---

## Test / acceptance

- [ ] Manual: single run shows plausible durations; failed MCP stage visible when induced in dev.
