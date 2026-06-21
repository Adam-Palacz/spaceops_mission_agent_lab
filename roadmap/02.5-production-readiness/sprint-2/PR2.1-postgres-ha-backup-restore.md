# PR2.1 - Postgres HA posture and backup/restore drill

## Description

Move Postgres from "persistent enough for stage" toward a production-pilot posture. The immediate
requirement is a tested backup and restore drill; managed HA can be selected where available.

## Requirements

- Decide production-pilot Postgres target: managed cloud DB, in-cluster operator, or documented
  staged transition.
- Define backup schedule, retention, encryption, and restore owner.
- Execute restore drill using representative data: incidents, audit, approvals, checkpoints,
  queue ledger, and LLM usage ledger.
- Record RTO/RPO and known data-loss boundaries.

## Checklist

- [ ] ADR/runbook updated with Postgres production posture.
- [ ] Backup job or managed backup configuration documented.
- [ ] Restore drill executed.
- [ ] Data integrity checks after restore documented.
- [ ] RTO/RPO recorded.

## Test requirements

- Automated or manual restore verification steps.
- Link tests for runbook/ADR references.

