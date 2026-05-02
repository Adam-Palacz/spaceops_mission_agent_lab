# PS2.2 — Incident detail + evidence panel

| Field | Value |
|-------|-------|
| **Task ID** | PS2.2 |
| **Status** | Todo |

---

## Description

**Incident detail** view: agent summary / report text, structured **evidence** (citations, snippets,
`doc_id`, tool output summaries — not raw secrets), and clear separation between “model narrative” vs
“grounded references”.

---

## Requirements

- [ ] Detail route from list (PS2.1): `/incidents/[id]` or equivalent.
- [ ] Sections: **Summary / report**, **Evidence** (citations list with doc_id + snippet preview), **Tool outcomes** (compact).
- [ ] Handles missing report / partial run gracefully.
- [ ] No full dump of internal prompts in UI (operational focus).

---

## Checklist

- [ ] Map `AgentState` / API response fields to UI components (reuse types from `apps/agent/state` or API DTOs).
- [ ] Truncate long snippets with expand/collapse.
- [ ] Link forward to run timeline (PS2.3) and trace (PS2.5) where applicable.

---

## Test / acceptance

- [ ] Manual: open at least two fixture incidents (clear anomaly + escalation path) and verify evidence renders.
