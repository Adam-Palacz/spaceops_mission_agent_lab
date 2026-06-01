# Phase: Next-Gen Autonomy (L3–L4)

Extend SpaceOps from **L1/L2** (MVP + production scale) toward **L3 assisted** and **L4 supervised**
autonomy — per [03-next-gen-autonomy.md](../03-next-gen-autonomy.md).

**Entry:** PS6 (minimum) + recommended PS7.1 (stage cloud) for demos in a prod-like environment.

---

## Autonomy levels (summary)

| Level | What we add |
|-------|-------------|
| **L1/L2 (now)** | Single graph, evidence, OPA, HITL approve/reject, eval gates |
| **L3 (NG1–NG2)** | Flight Director + specialists; collaborative planning |
| **L4 (NG3–NG5)** | Compliance scrubber, edge SLM, GraphRAG multi-hop |

---

## Sprint map

| Sprint | Folder | Theme (vision doc) | Goal |
|--------|--------|-------------------|------|
| **NG1** | [sprint-1/](sprint-1/) | Theme 1 — Multi-agent | Supervisor + 2 specialist agents, merge + audit |
| **NG2** | [sprint-2/](sprint-2/) | Theme 2 — Collaborative HITL | Plan edit, feedback, replan |
| **NG3** | [sprint-3/](sprint-3/) | Theme 3 — Compliance gateway | Redaction before LLM, policy per env |
| **NG4** | [sprint-4/](sprint-4/) | Theme 4 — Edge / air-gap SLM | Offline mode, degraded guarantees |
| **NG5** | [sprint-5/](sprint-5/) | Theme 5 — GraphRAG | Dependency graph + hybrid retrieval + evals |

Estimate: **~2 weeks per sprint**, 3–4 tasks each.

---

## Scope rules

- **OPA and approval** apply to every agent and every write action.
- **Evals** before every merge — new paths need new fixtures (including multi-hop in NG5).
- **Fail-closed** unchanged (goals NF8).
- Do not pull Theme 3–5 into NG1 — ordering reduces “half-L4” risk.

---

## Backlog outside NG

| Item | Where |
|------|--------|
| BL-003 | Closed (compose) — [TRIAGE](../backlog/TRIAGE.md) |
| BL-004 | PS7.7 or after NG4 |
| BL-005 | PS7.8 (platform ops) — different domain than mission agent |

---

## How to work

- Tasks: `NGx.y-*.md`, status in sprint `BOARD.md`.
- Vision detail: [03-next-gen-autonomy.md](../03-next-gen-autonomy.md) (themes 1–5).
- Project goals: [goals.md](../goals.md).
