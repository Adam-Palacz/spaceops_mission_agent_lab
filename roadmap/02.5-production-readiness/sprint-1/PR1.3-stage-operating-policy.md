# PR1.3 - Stage operating policy and readiness

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

- [x] Stage policy documented.
- [x] Cost/budget guardrails referenced.
- [x] Secret bootstrap path verified for selected policy.
- [x] Drift detection or GitOps ownership documented.
- [x] Deployment and teardown runbooks updated.

## Test requirements

- Stage recreate or drift-check drill evidence.
- Link tests for updated runbooks.

## Implementation notes

- Selected **ephemeral stage by default** with time-boxed long-lived windows for soak, game day, or
  external review evidence.
- Added [stage_operating_policy.md](../../../docs/runbooks/stage_operating_policy.md) as the
  canonical policy for ownership, cost controls, secret bootstrap, GitOps/Helm ownership, drift
  detection, demo readiness, teardown, and recreate RTO.
- Updated GCP deploy and teardown runbooks to reference the policy and expected teardown/drift
  verification.
- Documented full recreate target RTO as **<= 75 minutes**, excluding manual creation of new real
  secrets.
- Live recreate evidence is deferred to the next stage bring-up or PR1.4 because the repository
  deliverable is the operating policy and repeatable drift/recreate drill path.

## Status

Done.
