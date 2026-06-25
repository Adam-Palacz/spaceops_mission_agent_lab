# PR1 Sprint Review

## Verdict

PR1 is complete as the Production Readiness observability and reliability baseline. The sprint now
has live GKE evidence for monitoring, SLO rules, stage operating policy, and PR1.4 pilot-short
soak/failure recovery.

## Completed Tasks

| Task | Result | Evidence |
|------|--------|----------|
| PR1.1 | Done | Helm monitoring overlay with Prometheus, Grafana, OTel, NATS exporter, and postgres exporter. |
| PR1.2 | Done | SLO rules loaded in Prometheus; final alert state empty after PR1.4 restore. |
| PR1.3 | Done | Ephemeral-first stage policy with time-boxed long-lived windows. |
| PR1.4 | Done | [PR1.4 pilot-short report](evidence/PR1.4-pilot-short-2026-06-23.json). |

## PR1.4 Live Summary

- Stable stage profile: 2 non-preemptible `e2-standard-4` nodes via
  `terraform.pr14-stable.tfvars.example`.
- Pilot-short window: 2026-06-23 17:34:43-18:06:03 Europe/Warsaw.
- Soak result: 10/10 smoke + Scenario A/B cycles passed, plus final extension smoke.
- Failure matrix: F1, F3, F4, F5, F6, F7 passed; F2 is not applicable because Variant A
  `agent-worker` is not enabled in this stage profile.
- Final restore: Helm release `spaceops` revision 4, status `deployed`.
- Final observability: Prometheus targets up, SLO rules health OK, alerts `[]`.

## Residual Notes

- Scenario A still reports no citation refs on GKE, but report + evidence are present and this is
  already documented as a KB/indexing boundary, not a PR1 blocker.
- F2 must be repeated when Variant A agent-worker is promoted to stage.
- The PR1.4 stable profile is intentionally more expensive than the default lab profile and should
  remain time-boxed.
