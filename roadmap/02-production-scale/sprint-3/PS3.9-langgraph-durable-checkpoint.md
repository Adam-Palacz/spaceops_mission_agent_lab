# PS3.9 — LangGraph durable checkpoint (Postgres or equivalent)

| Field | Value |
|-------|-------|
| **Task ID** | PS3.9 |
| **Status** | Todo |

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

- [ ] ADR: choice of checkpointer backend, thread/run id strategy, retention, and interaction with replay.
- [ ] Implementation wired into `apps/agent/graph.py` (or documented wrapper) behind feature flag
      defaulting **off** in pure-file MVP until Postgres is available.
- [ ] Automated test: simulate interrupt → resume and assert state continuity (or documented limitation).
- [ ] Runbook note: operator steps when a pod dies mid-run (resume vs re-run from replay).

---

## Dependencies

- PS3.2 (offset/idempotency) must not contradict checkpoint semantics; document ordering **worker message → graph step**.

---

## Out of scope (defer)

- Full CCSDS / space-link simulation (Phase 3 “space-like” hooks remain PS3.6–PS3.7).
