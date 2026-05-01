# PS1.7 — Guardrails minimum hardening

| Field | Value |
|-------|--------|
| **Task ID** | PS1.7 |
| **Status** | Done |

---

## Description

Strengthen minimum fail-closed behavior so runs escalate when evidence is missing, tools fail, or
signals conflict. This sprint hardening ensures no unsafe “best guess” action path sneaks in.

---

## Requirements

- [x] Mandatory escalation on missing evidence.
- [x] Mandatory escalation on tool timeout/failure (distinct from empty result where possible).
- [x] Mandatory escalation on contradictory evidence/signals.
- [x] Output schemas remain enforced for report and escalation packets.
- [x] Guardrail decisions are traceable in audit entries.

---

## Checklist

- [x] Review and tighten escalation decision rules.
- [x] Standardize tool outcome semantics (`success` / `empty` / `failure`).
- [x] Add contradiction detection heuristic/rule in decision path.
- [x] Extend tests for no-evidence, tool-failure, and conflict scenarios.
- [x] Update docs/runbooks with new escalation expectations.

---

## Test requirements

- [x] Must-escalate scenarios pass in evals.
- [x] Tool failure leads to escalation with clear reason.
- [x] No run silently proceeds with missing evidence.
