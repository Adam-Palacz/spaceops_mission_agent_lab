# BL-005 — AI-assisted incident triage agent (queue/DLQ/MCP)

| Field | Value |
|-------|--------|
| **Backlog ID** | BL-005 |
| **Type** | Future concept / operations automation backlog |

---

## Description

Define and implement an AI-assisted incident triage capability that starts working as soon as queue/DLQ/MCP symptoms appear:
collect operational evidence automatically, produce ranked hypotheses, and suggest safe next commands.

Scope for first delivery is diagnosis and recommendations (read-only first), not autonomous remediation.

---

## Requirements

- [ ] Define a structured incident snapshot schema (services health, DLQ sample, replay dry-run summary, key logs, DB counters).
- [ ] Build read-only triage collector CLI/script to gather evidence and emit machine-readable output (JSON).
- [ ] Add LLM-assisted hypothesis + recommendation layer with confidence and rationale.
- [ ] Enforce execution safety gates: no write/apply actions without explicit human approval.
- [ ] Keep scope split by domain: queue/DLQ transport symptoms vs MCP breaker/lossy-link symptoms.
- [ ] Persist incident report and decisions for audit trail.

---

## Checklist

- [ ] Create an "AI-assisted mode" section in queue/DLQ runbook with command examples.
- [ ] Add a dedicated incident agent profile (prompt/policy) with explicit tool permissions.
- [ ] Add guardrails for dangerous actions (`--apply`, service restart, migration) as approval-only.
- [ ] Add confidence threshold policy (low confidence -> escalate to human/on-call).
- [ ] Add environment-aware handling (local Docker vs CI vs production-like host).
- [ ] Define ownership boundary between operator and agent (RACI-lite).

---

## Test requirements

- [ ] Deterministic input fixture produces stable triage JSON schema.
- [ ] For known synthetic incidents, top hypothesis matches expected class (e.g. DB down, NATS unavailable, MCP breaker-open).
- [ ] Agent never executes write actions without explicit approval signal.
- [ ] Generated recommendation list contains at least one safe verification command before any risky action.
- [ ] Audit artifact includes timestamp, evidence sources, suggested steps, and final human decision.

