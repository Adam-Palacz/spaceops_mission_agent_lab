# BL-005 — AI-assisted incident triage agent (queue/DLQ/MCP)

| Field | Value |
|-------|--------|
| **Backlog ID** | BL-005 |
| **Type** | Future concept / operations automation backlog |

> **Done (2026-06-03):** Read-only MVP via PS7.8 — `scripts/platform_ops_triage.py`, `apps/platform_ops/`.

---

## Description

Define and implement an AI-assisted incident triage capability that starts working as soon as queue/DLQ/MCP symptoms appear:
collect operational evidence automatically, produce ranked hypotheses, and suggest safe next commands.

Scope for first delivery is diagnosis and recommendations (read-only first), not autonomous remediation.

---

## Requirements

- [x] Define a structured incident snapshot schema (services health, DLQ sample, replay dry-run summary, key logs, DB counters).
- [x] Build read-only triage collector CLI/script to gather evidence and emit machine-readable output (JSON).
- [x] Add LLM-assisted hypothesis + recommendation layer with confidence and rationale.
- [x] Enforce execution safety gates: no write/apply actions without explicit human approval.
- [x] Keep scope split by domain: queue/DLQ transport symptoms vs MCP breaker/lossy-link symptoms.
- [x] Persist incident report and decisions for audit trail.

---

## Checklist

- [x] Create an "AI-assisted mode" section in queue/DLQ runbook with command examples.
- [x] Add a dedicated incident agent profile (prompt/policy) with explicit tool permissions.
- [x] Add guardrails for dangerous actions (`--apply`, service restart, migration) as approval-only.
- [x] Add confidence threshold policy (low confidence -> escalate to human/on-call).
- [x] Add environment-aware handling (local Docker vs CI vs production-like host).
- [x] Define ownership boundary between operator and agent (RACI-lite).

---

## Test requirements

- Deterministic input fixture produces stable triage JSON schema.
- For known synthetic incidents, top hypothesis matches expected class (e.g. DB down, NATS unavailable, MCP breaker-open).
- Agent never executes write actions without explicit approval signal.
- Generated recommendation list contains at least one safe verification command before any risky action.
- Audit artifact includes timestamp, evidence sources, suggested steps, and final human decision.

**Verified:** `tests/test_platform_ops_ps78.py`.
