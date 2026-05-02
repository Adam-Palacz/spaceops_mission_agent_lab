# PS1 — Sprint review

**Sprint:** Production Scale — Sprint 1 (PS1.1–PS1.9)  
**Board:** [BOARD.md](BOARD.md) — all tasks **Done**  
**Date:** 2026-05-02 (review)

---

## Executive summary

PS1 delivered a **repeatable operational baseline** on top of the MVP: versioned contracts, auditable DB evolution, replay capture + CLI/API, a thin LLM gateway contract, guardrail hardening, **deterministic CI eval gates** (must-escalate + evidence/citations), and **distributed tracing** with W3C propagation into MCP. The sprint goal from [README.md](README.md) is met; remaining work is mostly **environment parity** (Docker vs laptop) and **production hardening** called out in runbooks, not missing PS1 scope.

---

## Goals vs outcomes

| README outcome | Status |
|----------------|--------|
| Versioned data contracts + schema export | Done (PS1.1); validated in tests per task file |
| Alembic (or equivalent) + contract-aligned tables | Done (PS1.3); CI runs upgrade/downgrade/upgrade |
| Replay baseline + compare classification/escalation | Done (PS1.4–PS1.5); `tests/test_replay_*.py`, `apps/replay/` |
| CI: must-escalate + evidence/citation expectations | Done (PS1.8); `.github/workflows/ci.yml` `evals` job |
| Tracing: W3C propagation, semantic spans Agent → MCP | Done (PS1.9); tests under `tests/test_ps19_tracing.py`, OTel/Jaeger path |

---

## Definition of Done (sprint checklist)

Aligned with [README.md](README.md); evidence is repo-local (paths / CI).

1. **Contracts v1 validated in tests** — Covered by contract/export tests and ingest paths (see PS1.1/PS1.2 task notes).
2. **Migrations repeatable and documented** — `alembic/` baseline; CI job **Migration smoke** in `.github/workflows/ci.yml`.
3. **Replay runnable for regression** — `python -m apps.replay...` / scripts + `tests/test_replay_workflow.py`, `test_replay_cli.py`.
4. **CI: ≥1 must-escalate + ≥1 evidence gate** — `evals.scoring --case-id must-escalate-no-evidence` and `--case-id citation-present` before full eval run.
5. **Two demo scenarios E2E** — Still the north star for demos; not re-run as part of this document; treat as **release smoke** before tagging.

Items 1–4 are satisfied in automation; item 5 remains a **manual / staging** check unless wired into a dedicated smoke job.

---

## What shipped (by theme)

- **Data plane:** contracts, ingest validation, dedupe by `event_id`, Postgres alignment (PS1.1–PS1.3).
- **Reproducibility:** run metadata, payload hashing, replay CLI/API and diff detection (PS1.4–PS1.5).
- **LLM discipline:** gateway `generate`, metadata logging, limits (PS1.6).
- **Safety:** escalation and output constraints tightened (PS1.7).
- **Quality gates:** eval suite structure + CI must-escalate + citation-required cases (PS1.8).
- **Observability:** OTLP export, context propagation into MCP/KB, semantic spans and decision-summary style tags (PS1.9).

---

## Operational lessons (same timeframe as PS1 close-out)

These were **not PS1 board items** but surfaced when running the full Docker stack + Jaeger:

| Topic | Lesson |
|-------|--------|
| MCP **421** | FastMCP defaults + DNS rebinding `Host` check rejected Docker service names; fixed via `TransportSecuritySettings` + documented in `apps/mcp/README.md`. |
| KB **Postgres host** | `.env` `localhost` is wrong inside containers; Compose override for `kb-mcp` `DATABASE_URL` → `postgres:5432` with same `${POSTGRES_*}` credentials. |
| **pgvector query** | Query embeddings must bind as **`numpy.ndarray`**, not plain `list`, or Postgres sees `numeric[]` and `<=>` fails. |

They improve **runbook truth** and should be assumed for any PS2 “compose-first” acceptance.

---

## Risks and carryover

| Risk | Mitigation |
|------|------------|
| `DATABASE_URL` override in Compose uses URL interpolation; passwords with URL-reserved characters need encoding | Documented in `apps/mcp/README.md`; consider secret-mounted URL in stricter envs. |
| MCP transport security **off** in lab | Re-enable with explicit `allowed_hosts` / proxy before any public MCP exposure. |
| Demo scenarios not in CI as full E2E | Optional PS2: one compose smoke job or nightly workflow. |
| Eval job depends on `OPENAI_API_KEY` / optional secrets | Already gated in workflow; keep secrets hygiene in fork/PR policy. |

---

## Recommendation

**Close PS1** from a planning perspective: board is green, CI covers migrations + tests + deterministic eval gates, tracing story is credible. **Start PS2** with UI thin slice or streaming (per parent roadmap) and optionally promote “two demo scenarios” into automated smoke.

---

## Actions captured in repo

- [README.md](README.md) — Definition of Done checkboxes updated to reflect verification above.
- This file — single place for retrospective and sign-off.
