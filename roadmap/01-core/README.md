# Phase: Core (Sprint 1 + Sprint 2)

Delivers the full pipeline to Report (S1) and Act + OPA + approvals + injection suite + dashboards (S2). See [../roadmap_F1.md](../roadmap_F1.md) for the source.

---

## Sprints

| Sprint | Folder | Goal |
|--------|--------|------|
| **Sprint 1** | [sprint-1/](sprint-1/) | Ingest → Triage → Investigate → Decide → Report + evals + OTel + audit log + escalation. |
| **Sprint 2** | [sprint-2/](sprint-2/) | Act (safe + restricted), OPA fail-closed, approval API, injection suite, Prometheus/Grafana. |
| **Sprint 3** | sprint-3/ | Technical debt management (LLM/prompt lifecycle, resiliency patterns, infra/sec hygiene, process). |

---

## Instructions for AI

- Work **one task at a time** from the sprint folder; open the task’s .md file (e.g. `sprint-1/S1.4-fastapi-ingest.md`) for requirements and checklist.
- After completing a task, update that sprint’s **BOARD.md** (set status to Done).
- Do not add tasks outside the existing BOARD without creating a matching task .md and updating the BOARD.
- Dependencies: S1 must be complete (or at least S1.1–S1.4) before S2; S2.3–S2.5 depend on S2.1–S2.2 and OPA (S2.4).
