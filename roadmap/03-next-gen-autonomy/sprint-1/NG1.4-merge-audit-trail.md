# NG1.4 — Flight Director merge + per-agent audit

| **Task ID** | NG1.4 | **Status** | Todo |

## Description

Merge specialist findings into the existing Plan/Report output while preserving per-agent provenance.
The Flight Director is responsible for resolving conflicts, carrying uncertainty forward, and sending
all proposed actions through the existing OPA/HITL path.

## Requirements

- [ ] Merge contract accepts one or more specialist findings.
- [ ] Trace spans and audit records include `agent_id`, `specialist_role`, and routing decision metadata.
- [ ] Conflicting specialist findings produce an explicit conflict section or escalation.
- [ ] Merged actions retain evidence links and policy context.

## Acceptance

- [ ] Plan/Report output remains backward-compatible for downstream consumers.
- [ ] Audit trail shows which specialist produced each finding.
- [ ] OPA evaluates merged actions exactly once at the final action boundary.
- [ ] Tests cover single-specialist, multi-specialist, conflict, and no-evidence cases.

## Non-goals

- No UI changes beyond showing existing Plan/Report fields.
- No durable queue/worker split; PS7.3 covers that platform pattern.
