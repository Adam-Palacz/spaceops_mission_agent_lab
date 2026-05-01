# PS1.9 — Distributed tracing + W3C context propagation

| Field | Value |
|-------|--------|
| **Task ID** | PS1.9 |
| **Status** | Todo |
| **Source** | Backlog: [BL-001-monitoring-improvement-analysis.md](../../backlog/BL-001-monitoring-improvement-analysis.md) |
| **Severity** | Critical / Blocker for production observability |

---

## Description

Current tracing works inside single processes, but distributed trace continuity across
Agent -> MCP services is incomplete. This blocks reliable root-cause analysis (RCA) in a
multi-service path and weakens observability confidence for production.

This task implements end-to-end context propagation and semantic tracing behavior, so one
incident run can be traced as a single coherent flow in Jaeger.

---

## Requirements

- [ ] Add W3C context injection in Agent outbound MCP calls (`traceparent`, `tracestate`).
- [ ] Add W3C context extraction in MCP servers (`telemetry`, `kb`, `ticket`, `gitops`) so spans attach to parent trace.
- [ ] Add explicit semantic spans around critical agent flow boundaries (`decide`, `act`, OPA evaluation, MCP execution).
- [ ] Ensure span status is set to `ERROR` on failures (e.g. OPA deny/error path, MCP call failures).
- [ ] Ensure sensitive values (tokens/secrets/credentials) are never exported as span attributes.
- [ ] Keep report trace links correct: no fake trace URL when tracing/export is disabled.

---

## Checklist

- [ ] Implement context propagation hooks in `apps/agent/mcp_client.py`.
- [ ] Update all MCP servers to extract incoming trace context and continue trace.
- [ ] Add/update tracing helpers for consistent attribute naming (`incident_id`, `run_id`, `tool`, `outcome`).
- [ ] Add tests proving distributed trace continuity for at least one E2E run.
- [ ] Add tests proving error spans are marked correctly in failure scenarios.
- [ ] Update docs/runbook with a short verification flow for distributed tracing.

---

## Test requirements

- [ ] E2E run produces a single continuous trace across Agent and at least one MCP service.
- [ ] Forced OPA/MCP error path creates span(s) with `ERROR` status.
- [ ] Trace link in report is valid only when tracing/export is enabled.
- [ ] No secrets appear in exported span attributes or structured logs.
