# PR1.3 - Long-lived stage policy and readiness

## Description

Decide and document whether stage is long-lived or intentionally ephemeral. Production readiness
requires a reliable stage operating model, not ad-hoc cloud bring-up before demos.

## Requirements

- Choose one policy:
  - long-lived stage with cost controls and scheduled scale-down, or
  - ephemeral stage with tested recreate time and secret bootstrap path.
- Define ownership, budget limits, teardown rules, and demo readiness checklist.
- Document how GitOps/Helm ownership is selected and how drift is detected.
- Record expected RTO for recreating stage.

## Checklist

- [ ] Stage policy documented.
- [ ] Cost/budget guardrails referenced.
- [ ] Secret bootstrap path verified for selected policy.
- [ ] Drift detection or GitOps ownership documented.
- [ ] Deployment and teardown runbooks updated.

## Test requirements

- Stage recreate or drift-check drill evidence.
- Link tests for updated runbooks.

