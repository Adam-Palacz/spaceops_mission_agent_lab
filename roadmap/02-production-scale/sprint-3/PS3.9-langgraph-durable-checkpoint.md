# PS3.9 — LangGraph durable checkpoint (Postgres or equivalent)

| Field | Value |
|-------|-------|
| **Task ID** | PS3.9 |
| **Status** | Done |

---

## Problem statement

**Input replay** (PS1.4–PS1.5) re-runs the pipeline from scratch from stored inputs; it does **not**
restore in-flight LangGraph state after a **process restart** (OOM kill, rollout, node loss).
For long-running or multi-step investigations, we need an explicit **checkpoint / resume** story so
orchestrator restarts do not silently discard mid-graph reasoning.

---

## Description

Introduce a **durable checkpointer** for the agent graph (e.g. LangGraph `PostgresSaver` / official
Postgres checkpointer integration, or an ADR-chosen equivalent) backed by the same operational
Postgres used elsewhere. Define **what is persisted** (per-thread / per-run keys, TTL if any),
how **resume** is triggered (same `run_id`, operator action), and how this coexists with **queue
consumers** (PS3.2–PS3.4) without double-execution.

---

## Requirements

- [x] ADR captured: backend choice, key strategy, retention posture, replay/queue interaction.
- [x] Implementation wired into `apps/agent/graph.py` via durable wrapper behind feature flag
      (`AGENT_DURABLE_CHECKPOINT_ENABLED`, default **off**).
- [x] Automated test: interrupt → resume continuity covered.
- [x] Runbook note added: operator decision path for resume vs replay.

Implemented artifacts:
- `docs/adr/0003-langgraph-durable-checkpoint-postgres.md`
- `apps/agent/checkpointing.py`
- `apps/agent/graph.py` (durable runner integration)
- `apps/api/main.py` (`POST /runs/resume` operator trigger)
- `tests/test_durable_checkpoint_resume.py`
- `docs/runbooks/replay_workflow.md` (PS3.9 operator note)

---

## Dependencies

- PS3.2 (offset/idempotency) must not contradict checkpoint semantics; document ordering **worker message → graph step**.

---

## Out of scope (defer)

- Full CCSDS / space-link simulation (Phase 3 “space-like” hooks remain PS3.6–PS3.7).
