# NG1.2 — Power specialist agent

| **Task ID** | NG1.2 | **Status** | Todo |

## Description

Add a Power specialist agent behind the NG1 supervisor. The specialist focuses on bus voltage,
state of charge, battery margins, load shedding, and power-safe recommendations.

## Requirements

- [ ] Narrow system prompt and tool scope for Power-only analysis.
- [ ] Structured findings schema with evidence references, confidence, and proposed actions.
- [ ] Fixture telemetry covers at least bus voltage and state-of-charge anomalies.
- [ ] Specialist output is advisory until merged by the Flight Director.

## Acceptance

- [ ] Power-related fixture routes to the Power specialist.
- [ ] Output cites evidence and does not invent telemetry channels.
- [ ] Restricted actions still pass through existing OPA/HITL controls after merge.
- [ ] Unit tests cover normal, degraded, and missing-evidence paths.

## Non-goals

- No autonomous load-shedding execution.
- No new MCP server in NG1.2 unless the existing telemetry interface cannot represent required channels.
