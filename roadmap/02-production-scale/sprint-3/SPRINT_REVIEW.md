# PS3 — Sprint review

**Sprint:** Production Scale — Sprint 3 (PS3.1–PS3.10)  
**Board:** [BOARD.md](BOARD.md) — all tasks **Done**  
**Date:** 2026-05-08 (review)

---

## Executive summary

PS3 delivered the full resilience slice for queue-first operations: **NATS-first ingest with idempotent persistence**, **retry + DLQ + replay**, burst/disruption simulations (drop/dup/reorder/contact windows), an operator runbook for queue incidents, and closure of two major cross-cutting gaps from phase README: **durable checkpoint/resume for agent graph** (PS3.9) and **MCP lossy-link breaker/escalation proofs** (PS3.10). Sprint goal from [README.md](README.md) is met and creates a production-like bridge from ingest transport failures to controlled escalation semantics.

---

## Goals vs outcomes

| README outcome | Status |
|----------------|--------|
| Queue/offset model with idempotent consumer semantics | Done (PS3.1–PS3.2); ADR 0002 + JetStream ingest + persister dedupe |
| DLQ capture with diagnosable reasons + retry path | Done (PS3.3); `dlq_events` + retry/backoff + API read endpoint |
| Replay support for queued events | Done (PS3.4); `scripts/replay_queue.py` dry-run/apply patterns |
| Backpressure and disruption realism | Done (PS3.5–PS3.7); burst, out-of-order/dup/drop, contact-window hooks |
| Durable graph checkpoint + resume semantics | Done (PS3.9); ADR 0003, checkpoint store, `POST /runs/resume`, tests |
| MCP under lossy links proven with escalation behavior | Done (PS3.10); CI-safe chaos tests for breaker/retry/fail-closed |

---

## Definition of Done (sprint checklist)

Aligned with [README.md](README.md); evidence is repo-local (paths / tests).

1. **Backpressure does not crash ingest or corrupt offsets** — Covered by burst scenario tooling/tests (PS3.5) and queue-first ingest architecture (PS3.1–PS3.2).
2. **DLQ captures failed events with diagnosable reasons** — DLQ schema + API + tests (PS3.3).
3. **Replay works for queued events and preserves traceability** — queue replay CLI with dedupe and safe apply flow (PS3.4).
4. **At least one disruption scenario covered by automation** — satisfied by PS3.6 and PS3.7 automated scenarios/tests.
5. **PS3.9 checkpoint/resume documented + tested** — ADR 0003 + checkpoint integration + interrupt/resume test.
6. **PS3.10 breaker/retry + escalation path proven** — dedicated lossy-link test module + runbook triage bullets.

---

## What shipped (by theme)

- **Queue-first ingest path:** NATS/JetStream ingress with `event_id`/`Nats-Msg-Id` dedupe and async persister boundaries.
- **Reliability controls:** bounded retries, exponential backoff, DLQ persistence and inspection endpoint.
- **Recovery tooling:** queued-event replay with dry-run-first workflow and duplicate filtering.
- **Stress and disruption coverage:** burst/backpressure metrics, out-of-order/dup/drop simulation, contact-window buffering/flush behavior.
- **Operator readiness:** queue/DLQ recovery runbook with diagnostics, replay safety, and escalation criteria.
- **Durability of orchestration state:** Postgres-backed checkpoint snapshots for run continuity after restart and explicit resume action.
- **MCP transport hardening proof:** per-key circuit behavior + fail-fast/fail-closed semantics validated in tests.

---

## Operational lessons

| Topic | Lesson |
|-------|--------|
| **Host vs container network names** | Local host runs need `NATS_URL=nats://localhost:4222`, while in-compose services use `nats://nats:4222`; mismatch causes false outage symptoms. |
| **Schema/migration drift under active dev** | Queue/DLQ features depend on migrations being applied; missing table state (`dlq_events`) looks like runtime instability until DB is upgraded. |
| **Feature-flagged durability in tests** | Checkpoint mode must be controlled in tests to avoid `.env`-dependent behavior and regressions in legacy assertions. |
| **Transport resilience != domain safety** | Circuit breaker/checkpointing improve availability, but side-effect idempotency (ticket/PR actions) still requires explicit guards. |

---

## Risks and carryover

| Risk | Mitigation |
|------|------------|
| Checkpoint table retention growth over time | PS6 hardening should add retention/cleanup policy and operational alerts for checkpoint cardinality. |
| Resume path relies on Postgres availability | Keep feature flag off in minimal envs; runbook should prefer replay when durable store is unavailable. |
| MCP chaos tests are synthetic, not full network chaos infra | Current tests prove policy behavior; optional later step is environment-level chaos (tc/netem or proxy fault injection). |
| Replay/apply misuse during incidents | Runbook keeps dry-run-first and small-batch apply flow; maintain operator approval discipline. |

---

## Recommendation

**Close PS3** from planning and delivery perspective: board is fully green, DoD outcomes are covered, and major resilience gaps (checkpoint/resume + MCP lossy-link behavior) are now documented and test-backed. Next phase should focus on operationalization depth (cluster rollout, retention policies, and stricter automated chaos in production-like environments).

---

## Actions captured in repo

- [README.md](README.md) — sprint DoD checklist updated to reflect completion.
- This file — retrospective and sign-off for PS3.
