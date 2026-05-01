# PS1.8 — CI gate expansion (must-escalate + evidence-required)

| Field | Value |
|-------|--------|
| **Task ID** | PS1.8 |
| **Status** | Done |

---

## Description

Expand CI quality gates so core production behaviors are protected: mandatory escalation behavior
and evidence-required behavior must fail fast on regression.

---

## Requirements

- [x] CI includes at least one deterministic `must_escalate` gate.
- [x] CI includes at least one deterministic evidence/citation-required gate.
- [x] Gate failures provide actionable diagnostics (case ID + reason).
- [x] Existing unit/lint gates stay intact.
- [x] Local run instructions for these gates are documented.

---

## Checklist

- [x] Select or add representative eval cases for both gate classes.
- [x] Ensure cases are stable in local + CI execution environments.
- [x] Wire gate command(s) into CI workflow with clear fail conditions.
- [x] Add docs section on interpreting failed gates.
- [x] Add optional quick command for developers before PR.

---

## Test requirements

- [x] CI fails when must-escalate behavior regresses.
- [x] CI fails when evidence-required case escalates unexpectedly or lacks citations.
- [x] Running gate commands locally reproduces CI outcome.
