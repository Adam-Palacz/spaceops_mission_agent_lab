# Sprint 1 — Full pipeline to Report (Weeks 1–2)

**Goal:** One command runs the stack; ingest → triage → investigate → decide → report works end-to-end with basic evals and OTel traces. No act yet; evidence and escalation path in place.

---

## Outcomes

- Single-command local run; pinned deps + lockfile; reproducible fixtures.
- Repo structure (apps/, data/, kb/, evals/, infra/, docs/); Postgres + pgvector; OTel Collector + Jaeger.
- FastAPI: health, ingest webhook; agent trigger.
- LangGraph: Triage → Investigate (Telemetry + KB MCP) → Decide (citation grounding) → Report (summary, evidence, actions, rollback, trace link).
- Escalation: low confidence / no evidence / conflict / timeout → escalation packet.
- Audit log: append-only; schema per goals.md §4.6.
- Basic evals (triage + citation + “must escalate”); CI; deterministic.
- Structured logging (OTel); traces in Jaeger.

---

## Tasks

See **[BOARD.md](BOARD.md)** for status. Each task has a detail file: `S1.x-short-name.md`. Unit tests live in **tests/** and are added/expanded in **S1.14**.

---

## Definition of done (sprint)

- [ ] Single command brings up stack; ingest → report runs; report includes trace link.
- [ ] Escalation packet produced when conditions are met.
- [ ] Audit log has correct schema; append-only.
- [ ] Evals run in CI; triage, citation, escalation covered.
- [ ] Traces visible in Jaeger.
- [ ] Unit tests in **tests/** for API, audit log, and critical paths; pytest in CI.

---

## Instructions for AI

- Implement tasks in order S1.1 → S1.14 where possible; some can be parallelised (e.g. S1.5 fixtures while S1.4 is in progress).
- For each task: open `S1.x-*.md`, follow Requirements and Checklist, then run Test requirements. When done, set the task to Done in BOARD.md.
- Do not change the scope of a task without updating both the task .md and BOARD.
