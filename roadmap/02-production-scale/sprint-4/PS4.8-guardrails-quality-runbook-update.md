# PS4.8 — Guardrails and quality runbook update

| Field | Value |
|-------|-------|
| **Task ID** | PS4.8 |
| **Status** | Todo |

---

## Description

Consolidate PS4 safety/quality controls into an operator-friendly runbook: failed gates triage,
root-cause routing, and safe recovery steps.

---

## Requirements

- [ ] Update runbook(s) with PS4 gate triage flow and decision tree.
- [ ] Include symptom-to-action mapping for evidence, schema, injection, and MCP-policy failures.
- [ ] Link to replay, queue/DLQ, and MCP storm runbooks to avoid duplicated guidance.
- [ ] Provide junior-friendly execution order with explicit stop/escalate points.

---

## Checklist

- [ ] Commands are compose-oriented where relevant.
- [ ] Runbook includes examples of “what good looks like” outputs.
- [ ] Escalation criteria align with CI gate policy (PS4.7).

---

## Test / acceptance

- [ ] Tech reviewer walkthrough succeeds without source-code deep dive.
- [ ] At least one failed-gate scenario is resolved using only runbook instructions.
- [ ] Cross-links are valid and point to current docs.
