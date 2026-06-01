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
| **PS7** | [sprint-7/](sprint-7/) | Live GCP stage + monitoring/README backlog (hard: PS7.1–PS7.2, PS7.4–PS7.5); PS7b defers worker/budget/BL-004/005. |

**Next phase (L3/L4):** [03-next-gen-autonomy/](../03-next-gen-autonomy/) (NG1–NG5).

---

## Cross-cutting durability, safety, and evals

Gaps called out in external review (e.g. **graph checkpoint vs replay-only**, **MCP under LOS**,
**OPA/HITL test depth**, **ML observability beyond YAML evals**) are **owned** in sprints so they do
not fall between phases:

| Theme | Where it is tracked |
|-------|---------------------|
| **Durable LangGraph state** (Postgres checkpointer / resume after restart) | [PS3.9](sprint-3/PS3.9-langgraph-durable-checkpoint.md) — **PS3**; cluster hardening **PS6.11** — **PS6** |
| **MCP resilience proofs** (breaker open → escalation, chaos-style tests) | [PS3.10](sprint-3/PS3.10-mcp-resilience-lossy-links.md) — **PS3** (builds on existing S3.4 code) |
| **OPA fail-closed + HITL + integration tests** | **PS4** ([sprint-4/README.md](sprint-4/README.md)), especially PS4.4 / PS4.7; parent [Phase 4](../02-production-scale.md#phase-4--safety-controls--quality-gates-serious-mode) |
| **Golden runs + CI gating + behavior metrics** | **PS4** (PS4.5–PS4.6); **PS2.8** ([sprint-2/BOARD.md](sprint-2/BOARD.md)) for UI-adjacent baselines |
| **Optional LLM observability** (LangSmith / MLflow / RAGAS-style gates) | **PS5** PS5.8 + parent [Phase 4](../02-production-scale.md#phase-4--safety-controls--quality-gates-serious-mode) quality gates |

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
