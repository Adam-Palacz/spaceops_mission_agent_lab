# Phase: Production Readiness

This phase hardens SpaceOps from a production-like reference into a credible production pilot
baseline. It is a dedicated operations, reliability, security, and release-readiness track between
Production Scale and deep Next-Gen Autonomy.

Source strategy: [`../02.5-production-readiness.md`](../02.5-production-readiness.md).

---

## Sprint map

| Sprint | Folder | Goal |
|--------|--------|------|
| **PR1** | [sprint-1/](sprint-1/) | Observability, SLOs, long-lived stage policy, soak/failure tests. |
| **PR2** | [sprint-2/](sprint-2/) | Data durability, secrets rotation, security review, trace/log retention. |
| **PR3** | [sprint-3/](sprint-3/) | Release gates, incident drills, production pilot plan, final go/no-go review. |

---

## Autonomy dependency rule

- **NG1-NG2** may start in parallel when scoped to local or stage-lab proof.
- **NG3+** should wait for PR1 and PR2 hard gates, because compliance, edge mode, and GraphRAG need
  trustworthy observability, backup, secrets, and audit foundations.
- Any NG task that touches production-like deployment paths must inherit this phase's SLO, audit,
  release, and security gates.

---

## Definition of done for the phase

- All PR1-PR3 boards are Done.
- Production readiness review exists and records go/no-go status.
- Stage/prod promotion runbook references the new gates.
- Residual risks are either accepted with owners or converted to follow-up tasks.
- Next-Gen Autonomy README is updated with the production-readiness dependency.

---

## How to work in this phase

- Prefer PR1 -> PR2 -> PR3 order.
- Treat observability, backup/restore, secrets, and release gates as blocking requirements.
- Keep implementation evidence in docs/runbooks, tests, Helm/GitOps overlays, and sprint reviews.
- Do not mark a task Done with analysis only when the spec requires an executed drill.

