# PS1.7 — Guardrails minimum hardening

| Field | Value |
|-------|--------|
| **Task ID** | PS1.7 |
| **Status** | Todo |

---

## Description

Strengthen minimum fail-closed behavior so runs escalate when evidence is missing, tools fail, or
signals conflict. This sprint hardening ensures no unsafe “best guess” action path sneaks in.

---

## Requirements

- [ ] Mandatory escalation on missing evidence.
- [ ] Mandatory escalation on tool timeout/failure (distinct from empty result where possible).
- [ ] Mandatory escalation on contradictory evidence/signals.
- [ ] Output schemas remain enforced for report and escalation packets.
- [ ] Guardrail decisions are traceable in audit entries.

---

## Checklist

- [ ] Review and tighten escalation decision rules.
- [ ] Standardize tool outcome semantics (`success` / `empty` / `failure`).
- [ ] Add contradiction detection heuristic/rule in decision path.
- [ ] Extend tests for no-evidence, tool-failure, and conflict scenarios.
- [ ] Update docs/runbooks with new escalation expectations.

---

## Test requirements

- [ ] Must-escalate scenarios pass in evals.
- [ ] Tool failure leads to escalation with clear reason.
- [ ] No run silently proceeds with missing evidence.
