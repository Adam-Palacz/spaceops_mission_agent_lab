# NG1.1 — Supervisor graph ADR + routing skeleton

| **Task ID** | NG1.1 | **Status** | Todo |

## Description

Create ADR 0011 and a disabled-by-default routing skeleton for a Flight Director supervisor graph.
The supervisor routes incidents to subsystem specialists (initially Power and Thermal; ADCS remains
future scope) and merges their findings back into the existing Plan/Report path.

## Requirements

- [ ] ADR 0011 documents graph topology, routing contract, specialist boundaries, and rollback plan.
- [ ] Feature flag `MULTI_AGENT_ENABLED` defaults to off in every environment.
- [ ] Supervisor node has a typed input/output contract and does not bypass existing evidence, OPA, or HITL gates.
- [ ] Routing decisions are deterministic enough for fixture tests.

## Acceptance

- [ ] Existing single-agent path remains unchanged when `MULTI_AGENT_ENABLED=false`.
- [ ] ADR answers when to route to one specialist vs multiple specialists.
- [ ] Skeleton includes tests or fixtures proving the supervisor can select Power and Thermal routes.
- [ ] Docs state that NG1 does not add new write privileges.

## Non-goals

- No ADCS specialist implementation in NG1.1.
- No separate worker Deployment; PS7.3 covers Variant A if needed.
- No cloud requirement; local compose or minimal K8s is sufficient.
