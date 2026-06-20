# Backlog triage (2026-05-31)

Assessment of [items.md](items.md) against the post-**PS6** state (platform packaging closed).
Use this table when planning sprints — **status lives in the sprint BOARD**, not here.

| ID | Verdict | Rationale | Scheduled in |
|----|---------|-----------|--------------|
| **BL-001** | **Done (PS7.4)** | PS1.9 was tracing only; analysis delivered in [monitoring-production-analysis.md](../../docs/monitoring-production-analysis.md). | — |
| **BL-002** | **Still relevant (partial)** | READMEs exist under `apps/*` and parts of `docs/`, but not `data/`, `kb/`, `evals/`, many `roadmap/` subfolders. Onboarding value remains high (NF7). | **PS7.5** — documentation hygiene |
| **BL-003** | **Done — close** | `infra/docker-compose.yml` has `telemetry-mcp`, `kb-mcp`, persister, full stack; BL-003 goals met since PS1/compose hardening. | Archive in items.md; no new task |
| **BL-004** | **Future** | Multi-cloud GPU burst — sensible **after** live GCP (PS7) and stable gateway (PS5). Does not block MVP. | **PS7.7** (ADR + simulation) or later NG / Phase 7 Stage 4 |
| **BL-005** | **Relevant, different product** | Does **not** duplicate the mission agent (Triage→Report). This is a **platform ops** agent (queue, DLQ, MCP breaker) — SRE domain, not satellite anomaly telemetry. | **PS7.8** (read-only MVP) or separate track after PS7.1 |

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
| Production-ready / portfolio | PS6.10; PS7 closes **live cloud** stretch |
| Learning / reference | BL-002, portfolio; NG as innovation showcase |

---

## Maintenance actions

- [x] TRIAGE.md (this file)
- [ ] After PS7.4 / PS7.5 start — update rows in [items.md](items.md) (Disposition column)
- [ ] After NG1 — consider moving Theme 1–5 detail from [03-next-gen-autonomy.md](../03-next-gen-autonomy.md) into sprint links (vision file remains)
