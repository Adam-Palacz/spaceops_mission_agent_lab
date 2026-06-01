# NG1.3 — Thermal specialist agent

| **Task ID** | NG1.3 | **Status** | Todo |

## Description

Add a Thermal specialist agent behind the NG1 supervisor. The specialist focuses on component
temperatures, heater state, radiator assumptions, thermal limits, and safe-mode thermal risk.

## Requirements

- [ ] Narrow system prompt and tool scope for Thermal-only analysis.
- [ ] Structured findings schema compatible with the Flight Director merge contract.
- [ ] Fixture telemetry covers over-temperature, under-temperature, and missing sensor cases.
- [ ] Specialist explicitly marks uncertainty when thermal evidence is incomplete.

## Acceptance

- [ ] Thermal-related fixture routes to the Thermal specialist.
- [ ] Output cites telemetry and runbook evidence where available.
- [ ] Missing evidence results in escalation or uncertainty, not fabricated conclusions.
- [ ] Unit tests cover nominal, violation, and incomplete-data cases.

## Non-goals

- No thermal simulation engine.
- No autonomous heater command execution.
