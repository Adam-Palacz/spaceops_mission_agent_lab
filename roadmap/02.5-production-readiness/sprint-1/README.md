# PR1 - Observability and Reliability Baseline

**Goal:** make the K8s/stage platform observable and measurable enough to operate, debug, and
gate releases.

## Outcomes

- Prometheus/Grafana or managed monitoring is deployed for K8s stage through Helm or GitOps.
- SLO dashboard and alert rules cover API, agent worker, queue/DLQ, Postgres, LLM budget, and
  safety/eval regressions.
- Stage operating policy is explicit: ephemeral by default, with time-boxed long-lived windows only
  for soak, game day, or external review evidence.
- Soak, load, and failure tests produce evidence for readiness review.

## Definition of done

- [ ] PR1 board is complete.
- [ ] Stage monitoring is accessible and documented.
- [ ] SLO/alert rules are tested with at least one synthetic trigger.
- [ ] Stage policy is referenced from deployment and teardown runbooks.
- [ ] Soak/failure test results are attached or summarized in a sprint review.

See [BOARD.md](BOARD.md).
