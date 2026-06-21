# Backlog triage (2026-06-21)

Assessment of [items.md](items.md) against the post-**PS7** state and the new
[Production Readiness](../02.5-production-readiness/) phase.
Use this table when planning sprints — **status lives in the sprint BOARD**, not here.

| ID | Verdict | Rationale | Scheduled in |
|----|---------|-----------|--------------|
| **BL-001** | **Done (PS7.4)** | PS1.9 was tracing only; analysis delivered in [monitoring-production-analysis.md](../../docs/monitoring-production-analysis.md). | — |
| **BL-002** | **Done (PS7.5)** | Folder READMEs added under `data/`, `kb/`, `evals/`, `infra/`; apps and roadmap phase folders already covered. | — |
| **BL-003** | **Done — close** | `infra/docker-compose.yml` has `telemetry-mcp`, `kb-mcp`, persister, full stack; BL-003 goals met since PS1/compose hardening. | Archive in items.md; no new task |
| **BL-004** | **Done (PS7.7)** | ADR 0010 + simulation; live burst Phase 7. | — |
| **BL-005** | **Done (PS7.8)** | Read-only platform ops triage CLI; separate from mission agent. | — |

## Production readiness carryover

PS7 closed the backlog items above, but its monitoring and operations analysis created production
hardening work that now lives in [02.5-production-readiness](../02.5-production-readiness/), not in
the backlog pool.

| Source | Production Readiness owner | Notes |
|--------|----------------------------|-------|
| PS7b-M1 Prometheus/Grafana on K8s | [PR1.1](../02.5-production-readiness/sprint-1/PR1.1-k8s-monitoring-stack.md) | K8s metrics and dashboard deployment. |
| PS7b-M2 OTLP TLS + sampling | [PR1.1](../02.5-production-readiness/sprint-1/PR1.1-k8s-monitoring-stack.md) | Collector security, limits, and sampling. |
| PS7b-M3 trace retention / managed backend | [PR2.4](../02.5-production-readiness/sprint-2/PR2.4-retention-privacy.md) | Jaeger/Cloud Trace/Tempo retention decision. |
| PS7b-M4 SLO dashboard | [PR1.2](../02.5-production-readiness/sprint-1/PR1.2-slo-alerts.md) | SLO panels and alert rules. |
| PS7b-M5 Postgres metrics and alerts | [PR1.1](../02.5-production-readiness/sprint-1/PR1.1-k8s-monitoring-stack.md) | Exporter or managed DB metrics. |

---

## Recommendation: backlog vs sprint board

| Approach | When |
|----------|------|
| **Backlog pool (items.md + BL-xxx)** | Ideas, concept ADRs, “someday” — no status |
| **Sprint task (PS7.x / NG1.x) + BOARD** | Anything you plan to deliver in the next 2–8 weeks |
| **Note in BL-xxx** | After scheduling: `→ PS7.4` (like BL-001) — no Status column in items.md |

Do **not** maintain **two** boards with statuses (backlog + sprint) — they will drift.
Backlog = **pool**; closure = TRIAGE update + task **Done** on sprint BOARD.

---

## Alignment with [goals.md](../goals.md)

| Project goal | Backlog / phase |
|--------------|-----------------|
| Anomaly triage + evidence + safe act | Core — **delivered** (S1–S2, PS1–PS6); NG extends L3/L4 |
| Observability (OTel, Jaeger, metrics) | BL-001 closes **prod readiness analysis** gap, not new features |
| Production-ready / portfolio | PS6.10 and PS7 close reference/cloud proof; **02.5 Production Readiness** owns production-pilot gates |
| Learning / reference | BL-002, portfolio; NG as innovation showcase |

---

## Maintenance actions

- [x] TRIAGE.md (this file)
- [x] After PS7.4 / PS7.5 start — update rows in [items.md](items.md) (Disposition column)
- [ ] After PR1 — update this file with production-readiness evidence links
- [ ] After NG1 — consider moving Theme 1–5 detail from [03-next-gen-autonomy.md](../03-next-gen-autonomy.md) into sprint links (vision file remains)
