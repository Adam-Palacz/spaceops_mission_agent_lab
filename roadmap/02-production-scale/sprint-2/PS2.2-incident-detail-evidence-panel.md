# PS2.2 — Incident detail + evidence panel

| Field | Value |
|-------|-------|
| **Task ID** | PS2.2 |
| **Status** | Done |

---

## Description

**Incident detail** view: agent summary / report text, structured **evidence** (citations, snippets,
`doc_id`, tool output summaries — not raw secrets), and clear separation between “model narrative” vs
“grounded references”.

---

## Requirements

- [x] Detail route from list (PS2.1): `/incidents/[id]` or equivalent.
- [x] Sections: **Summary / report**, **Evidence** (citations list with doc_id + snippet preview), **Tool outcomes** (compact).
- [x] Handles missing report / partial run gracefully.
- [x] No full dump of internal prompts in UI (operational focus).

---

## Checklist

- [x] Map `AgentState` / API response fields to UI components (reuse types from `apps/agent/state` or API DTOs).
- [x] Truncate long snippets with expand/collapse.
- [x] Link forward to run timeline (PS2.3) and trace (PS2.5) where applicable.

---

## Implementation notes

- **UI:** `apps/ui/app/incidents/[runKey]/page.tsx` — sections: metadata, pipeline error, summary/rollback, proposed actions, evidence (notes + citation_refs + optional `citations[]`), escalation packet, tool outcomes (`act_results`), payload summary, trace link + PS2.3 placeholder, collapsible raw JSON.
- **Config:** `NEXT_PUBLIC_JAEGER_UI_URL` in `lib/config.ts` + `.env.example` when `report.trace_link` is missing but `trace_id` exists.

---

## Test / acceptance

- [x] Manual: open at least two fixture incidents (clear anomaly + escalation path) and verify evidence renders.
- [ ] Optional: Playwright or lightweight smoke test if repo already adopts E2E (otherwise defer).

---

## Follow-ups

- **PS2.3** replaces the static “timeline planned” line with real stage data.
- **PS2.4** may refine escalation layout if UX needs more than the current packet section.
