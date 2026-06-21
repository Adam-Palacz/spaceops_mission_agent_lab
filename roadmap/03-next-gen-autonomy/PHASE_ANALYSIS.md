# Phase Analysis: Next-Gen Autonomy

Date: 2026-06-21
Status: Planned
Scope: NG1-NG5

## Executive summary

Next-Gen Autonomy is a forward-looking L3/L4 autonomy phase. It is currently a plan, not an
executed phase: all NG1-NG5 sprint board items are still Todo.

The phase improves the intelligence and autonomy of the mission agent: multi-agent supervision,
collaborative planning, compliance-aware LLM redaction, offline/local SLM fallback, and GraphRAG.
It does not by itself complete all work needed for a fully production-operated system.

## Planned scope

| Sprint | Status | Purpose |
|--------|--------|---------|
| NG1 | Todo | Flight Director supervisor graph, Power/Thermal specialists, per-agent audit and merge. |
| NG2 | Todo | Collaborative HITL: plan edits, operator feedback, replan-with-constraints, UI support. |
| NG3 | Todo | Compliance-aware LLM gateway: redaction policy, scrubber integration, masking audit logs. |
| NG4 | Todo | Edge/air-gapped operation: dual-mode gateway, local SLM adapter, degraded-mode evals. |
| NG5 | Todo | GraphRAG: dependency graph, hybrid retrieval, multi-hop evals. |

## Strategic value

The phase addresses the main autonomy limitations left after Production Scale:

- moves from a single graph to a Flight Director plus specialist agents,
- makes HITL collaborative instead of approve/reject only,
- reduces external LLM data leakage risk through redaction,
- improves degraded/offline behavior through local SLM support,
- improves cross-subsystem reasoning through dependency graphs and multi-hop retrieval.

These are important for a credible L3/L4 mission-ops prototype.

## Production impact

If implemented well, this phase would make the system more capable and safer in complex scenarios.
It would especially strengthen:

- subsystem-specific reasoning,
- operator steering and auditability,
- compliance boundaries before external LLM calls,
- degraded-mode continuity,
- multi-hop root-cause analysis.

However, this phase is not a complete production hardening phase. Its scope is autonomy and
reasoning capability, not full platform operations.

## Does this create a production system?

No, not by itself.

Completing NG1-NG5 would likely produce a strong L3/L4 pre-production prototype or advanced
reference system. It would not automatically produce a production system ready for real mission
operations unless the following are also completed:

- managed HA Postgres and tested backup/restore,
- production-grade Prometheus/Grafana or managed monitoring in K8s,
- alerting, paging, SLOs, runbooks, and incident drills,
- hardened secrets lifecycle and rotation in the target environment,
- security review for redaction, audit, auth, and MCP boundaries,
- load, soak, and failure testing in a long-lived stage environment,
- formal release process and rollback gates,
- production data governance and retention policy,
- real integration contracts for telemetry, events, ticketing, GitOps, and operator identity.

## Recommended maturity target

Target after NG1-NG5: advanced pre-production / L3-L4 autonomy reference.

Target for true production: complete the dedicated
[Production Readiness](../02.5-production-readiness/) track, focused on operations, security,
reliability, and compliance.

## Recommended additions before execution

- Add explicit production-readiness acceptance criteria to each NG sprint.
- Require eval coverage for every new autonomy path before merge.
- Keep OPA, approval, audit, evidence, and fail-closed behavior mandatory for every specialist
  agent and every generated action.
- Add a separate production-hardening backlog, not mixed into autonomy feature work.
- Create a final NG phase review after all five sprint boards are complete.
