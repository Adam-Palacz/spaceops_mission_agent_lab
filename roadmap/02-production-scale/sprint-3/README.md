# Production Scale — Sprint 3 (PS3)

**Goal:** introduce streaming/backpressure realism and resilient processing with offset tracking,
DLQ handling, and replay support over queued events — **plus** durable agent execution and proven
MCP behaviour under unreliable links (so platform stress does not “lose the incident”).

---

## Outcomes

- Queue/offset processing model with idempotent consumer semantics.
- DLQ capture for failed processing and retry/replay path.
- Backpressure behavior tested (ingest remains stable under burst load).
- Space-like disruptions simulated (drop/dup/out-of-order/contact-window effects).
- **Durable LangGraph checkpointing** (Postgres-backed or ADR-equivalent) and **resume semantics** after process restarts (**PS3.9**).
- **MCP transport** proven under lossy-link / breaker-open scenarios with correct **escalation / audit**
  outcomes, building on existing S3.4 retry+circuit code (**PS3.10**).

---

## Tasks

See **[BOARD.md](BOARD.md)** for status of PS3.1–PS3.10.

| Spec | Topic |
|------|--------|
| [PS3.9-langgraph-durable-checkpoint.md](PS3.9-langgraph-durable-checkpoint.md) | Graph state survives restarts |
| [PS3.10-mcp-resilience-lossy-links.md](PS3.10-mcp-resilience-lossy-links.md) | MCP chaos + escalation proofs |

---

## Definition of done (sprint)

- [ ] Backpressure does not crash ingest or corrupt offsets.
- [ ] DLQ captures failed events with diagnosable reasons.
- [ ] Replay works for queued events and preserves incident traceability.
- [ ] At least one disruption scenario is covered by automated tests.
- [ ] **PS3.9:** ADR + checkpoint integration path documented; resume or explicit limitation covered by tests.
- [ ] **PS3.10:** At least one automated scenario proves breaker/retry + escalation path for MCP failures.

---

## Handoff

- **PS4:** expands OPA/HITL **integration tests** and CI gating on evidence/audit semantics (see sprint-4 README).
- **PS6:** operationalizes checkpointed workers in cluster (see sprint-6 BOARD PS6.11).
