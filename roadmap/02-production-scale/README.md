# Phase: Production Scale (Post-MVP)

This phase turns the completed Foundation MVP into a production-grade reference:
reproducibility, stronger safety gates, operational UI, streaming realism, backend portability,
and platform deployment patterns.

Source strategy: [`../02-production-scale.md`](../02-production-scale.md).

---

## Sprint map (2 weeks each)

| Sprint | Folder | Goal |
|--------|--------|------|
| **PS1** | [sprint-1/](sprint-1/) | Core operational hardening: contracts, migrations, replay baseline, stronger CI gates. |
| **PS2** | [sprint-2/](sprint-2/) | Operational UI + replay workflows + golden-run baselines. |
| **PS3** | [sprint-3/](sprint-3/) | Streaming/queue backbone, DLQ, and outage/backpressure resilience. |
| **PS4** | [sprint-4/](sprint-4/) | Expanded safety controls and measurable quality gates. |
| **PS5** | [sprint-5/](sprint-5/) | LLM backend portability (OpenAI/GPU optional), gateway controls, cost guardrails. |
| **PS6** | [sprint-6/](sprint-6/) | K8s/GitOps/cloud-ready packaging + portfolio-grade operational artifacts. |

---

## How to work in this phase

- Use each sprint folder in order (`sprint-1` -> `sprint-6`).
- In each sprint:
  - `README.md` = goal, outcomes, DoD.
  - `BOARD.md` = task status (`Todo | In progress | Done | Blocked`).
- Keep scope aligned to `roadmap/02-production-scale.md`; avoid adding non-goal “nice-to-have”
  items before current sprint DoD is met.

---

## Instructions for AI

- Prefer finishing one sprint before opening tasks in the next sprint.
- Treat safety and reproducibility tasks as blocking prerequisites for scale/platform tasks.
- When implementing, update the sprint `BOARD.md` status and keep docs/ops runbooks synchronized.
