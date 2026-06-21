# PR3.2 - Incident, on-call, and rollback drills

## Description

Convert runbooks into executed operational practice. A production pilot needs proof that operators
can detect, triage, mitigate, and roll back failures.

## Requirements

- Define incident classes: API outage, worker stuck, OPA unavailable, Postgres degraded, queue/DLQ
  growth, LLM backend outage, budget cap hit, unsafe-action regression.
- Run at least one game day covering detection, escalation, mitigation, and rollback.
- Define on-call roles, escalation path, and communication templates.
- Record timelines and improvements.

## Checklist

- [ ] Incident drill plan added.
- [ ] On-call/escalation roles documented.
- [ ] At least one game day executed.
- [ ] Rollback drill executed or reused from release gate evidence.
- [ ] Post-drill action items tracked.

## Test requirements

- Drill evidence and follow-up issue/task links.
- Alert firing or synthetic evidence for at least one incident class.

