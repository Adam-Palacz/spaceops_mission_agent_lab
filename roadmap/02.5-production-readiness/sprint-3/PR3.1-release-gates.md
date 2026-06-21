# PR3.1 - Release smoke/e2e promotion gates

## Description

Define and automate promotion gates so releases cannot move to stage/prod without health, scenario,
safety, and rollback evidence.

## Requirements

- Gate includes lint/tests, Helm template/lint, migration dry-run, health check, demo scenarios A/B,
  approval flow, OPA deny/fail-closed check, queue/DLQ check, and rollback readiness.
- Gate can run in CI or as a documented pre-promotion command.
- Gate output is stored as release evidence.
- Failed gate blocks promotion.

## Checklist

- [ ] Release gate command or CI workflow added.
- [ ] Gate covers health, scenarios, safety, queue, migration, and rollback readiness.
- [ ] Evidence artifact path documented.
- [ ] Environment promotion runbook updated.
- [ ] Failure behavior documented.

## Test requirements

- CI-safe dry-run where cloud credentials are absent.
- Stage execution evidence before phase closure.

