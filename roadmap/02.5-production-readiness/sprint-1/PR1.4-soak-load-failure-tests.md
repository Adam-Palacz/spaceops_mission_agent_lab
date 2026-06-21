# PR1.4 - Soak, load, and failure test pack

## Description

Add evidence that the system can run for longer than a demo and survive expected failures. This is
the production-readiness counterpart to unit and sprint-level CI tests.

## Requirements

- Define a stage soak test profile with duration, fixture mix, and acceptance criteria.
- Define load test limits for API, queue, and agent worker.
- Include failure scenarios: API pod restart, worker restart, OPA unavailable, Postgres restart,
  queue/DLQ pressure, LLM backend failure, and budget exhaustion.
- Capture results in a repeatable report.

## Checklist

- [ ] Soak/load/failure test plan added.
- [ ] Automation scripts or Make targets added where practical.
- [ ] Acceptance thresholds documented.
- [ ] At least one run executed and summarized.
- [ ] Failures become backlog/tasks with owners.

## Test requirements

- CI-safe dry-run or syntax check for scripts.
- Stage run evidence for the full profile before phase closure.

