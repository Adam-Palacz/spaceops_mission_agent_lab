# PS4.8 — Guardrails and quality runbook update



| Field | Value |

|-------|-------|

| **Task ID** | PS4.8 |

| **Status** | Done |



---



## Description



Consolidate PS4 safety/quality controls into an operator-friendly runbook: failed gates triage,

root-cause routing, and safe recovery steps.



---



## Requirements



- [x] Update runbook(s) with PS4 gate triage flow and decision tree.

- [x] Include symptom-to-action mapping for evidence, schema, injection, and MCP-policy failures.

- [x] Link to replay, queue/DLQ, and MCP storm runbooks to avoid duplicated guidance.

- [x] Provide junior-friendly execution order with explicit stop/escalate points.



---



## Checklist



- [x] Commands are compose-oriented where relevant.

- [x] Runbook includes examples of “what good looks like” outputs.

- [x] Escalation criteria align with CI gate policy (PS4.7).



---



## Test / acceptance



- [x] Tech reviewer walkthrough succeeds without source-code deep dive.

- [x] At least one failed-gate scenario is resolved using only runbook instructions.

- [x] Cross-links are valid and point to current docs.



---



## Deliverables



- `docs/runbooks/guardrails_quality_triage.md` — primary PS4.8 operator runbook

- `docs/runbooks/guardrails_minimum_hardening.md` — updated index + PS4 references

- `docs/runbooks/ci_gating_policy.md` — link to triage runbook

- `docs/README.md` — index entry

