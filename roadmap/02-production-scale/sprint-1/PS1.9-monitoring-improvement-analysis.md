# PS1.9 — Distributed tracing + W3C context propagation

| Field | Value |
|-------|--------|
| **Task ID** | PS1.9 |
| **Status** | Done |
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

- [x] Add W3C context injection in Agent outbound MCP calls (`traceparent`, `tracestate`).
- [x] Add W3C context extraction in MCP servers (`telemetry`, `kb`, `ticket`, `gitops`) so spans attach to parent trace.
- [x] Add explicit semantic spans around critical agent flow boundaries (`decide`, `act`, OPA evaluation, MCP execution).
- [x] Ensure span status is set to `ERROR` on failures (e.g. OPA deny/error path, MCP call failures).
- [x] Ensure sensitive values (tokens/secrets/credentials) are never exported as span attributes.
- [x] Keep report trace links correct: no fake trace URL when tracing/export is disabled.

---

## Checklist

- [x] Implement context propagation hooks in `apps/agent/mcp_client.py`.
- [x] Update all MCP servers to extract incoming trace context and continue trace.
- [x] Add/update tracing helpers for consistent attribute naming (`incident_id`, `run_id`, `tool`, `outcome`).
- [x] Add tests proving distributed trace continuity for at least one E2E run.
- [x] Add tests proving error spans are marked correctly in failure scenarios.
- [x] Update docs/runbook with a short verification flow for distributed tracing.

---

## Test requirements

- [x] E2E run produces a single continuous trace across Agent and at least one MCP service.
- [x] Forced OPA/MCP error path creates span(s) with `ERROR` status.
- [x] Trace link in report is valid only when tracing/export is enabled.
- [x] No secrets appear in exported span attributes or structured logs.
