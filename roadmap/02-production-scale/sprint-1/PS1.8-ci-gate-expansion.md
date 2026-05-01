# PS1.8 — CI gate expansion (must-escalate + evidence-required)

| Field | Value |
|-------|--------|
| **Task ID** | PS1.8 |
| **Status** | Todo |

---

## Description

Expand CI quality gates so core production behaviors are protected: mandatory escalation behavior
and evidence-required behavior must fail fast on regression.

---

## Requirements

- [ ] CI includes at least one deterministic `must_escalate` gate.
- [ ] CI includes at least one deterministic evidence/citation-required gate.
- [ ] Gate failures provide actionable diagnostics (case ID + reason).
- [ ] Existing unit/lint gates stay intact.
- [ ] Local run instructions for these gates are documented.

---

## Checklist

- [ ] Select or add representative eval cases for both gate classes.
- [ ] Ensure cases are stable in local + CI execution environments.
- [ ] Wire gate command(s) into CI workflow with clear fail conditions.
- [ ] Add docs section on interpreting failed gates.
- [ ] Add optional quick command for developers before PR.

---

## Test requirements

- [ ] CI fails when must-escalate behavior regresses.
- [ ] CI fails when evidence-required case escalates unexpectedly or lacks citations.
- [ ] Running gate commands locally reproduces CI outcome.
