## Phase 4 — Hardening Review

**Phase:** 01-foundation-mvp, 02-hardening (docs, runbooks, eval expansion, post-incident loop, model-shadow rollout)  
**Scope:** P4.1–P4.8  
**Status:** Hardening scope delivered; BOARD aligned to Done for all P4 tasks.

---

## 1. Executive summary

Phase 4 closed the gap between a feature-complete lab and a maintainable, production-style operating model. The team completed architecture and operator documentation, added practical runbooks for extending MCP and evals, improved retrieval quality with reranking, delivered an optional operational UI, expanded eval coverage to a wider deterministic suite, and introduced two key recurring reliability loops: post-incident learning and shadow model promotion gates. This means changes are now easier to operate, safer to ship, and easier to review. **Hardening goal achieved.**

---

## 2. Phase goal and assessment

**Goal (from 02-hardening):**  
*Deliver docs/runbooks and eval hardening so model and operational changes follow repeatable, reviewable, low-regression workflows.*

| Criterion | Status | Notes |
|-----------|--------|-------|
| Architecture documentation is complete and usable | ✅ | `docs/architecture.md` documents components, data flow, and technology choices. |
| Runbook for adding a new MCP exists | ✅ | `docs/runbooks/add_new_mcp.md` provides onboarding flow for MCP extension. |
| Runbook for adding eval cases exists | ✅ | `docs/runbooks/add_eval_case.md` documents schema, scoring, and CI path. |
| RAG reranking improves citation ordering path | ✅ | P4.4 introduces retrieval -> rerank -> return flow in KB search path. |
| Optional operator UI is available | ✅ | `apps/ui/` provides incidents + approvals views with approve/reject flow. |
| Eval suite is expanded and still deterministic | ✅ | Standard suite expanded to 20 cases; scoring keeps MoE checks and CI gate. |
| Post-incident learning loop is documented and executable | ✅ | Template + runbook + `scripts.reindex_kb` establish recurring learning cycle. |
| Shadow model rollout process is operational | ✅ | Scheduled/manual workflow + decision-report schema for model promotion. |

**Verdict:** Phase 4 **goal achieved**.

---

## 3. What was done — task by task

### P4.1 — Architecture documentation
- **Why:** Reduce onboarding time and ambiguity around component boundaries and data flow.
- **What:** Finalized `docs/architecture.md` with architecture overview, request/data flow, and rationale for core stack choices.

### P4.2 — Runbook: add new MCP
- **Why:** Make capability expansion repeatable without tribal knowledge.
- **What:** Added MCP onboarding runbook (`docs/runbooks/add_new_mcp.md`) with server template flow, registration, and agent wiring guidance.

### P4.3 — Runbook: add eval case
- **Why:** Ensure incidents and regressions can be converted quickly into automated checks.
- **What:** Added eval runbook (`docs/runbooks/add_eval_case.md`) covering case shape, scoring semantics, and local/CI verification flow.

### P4.4 — Reranker for RAG (NF5)
- **Why:** Improve relevance ordering for retrieved chunks and protect citation quality.
- **What:** Added configurable reranking stage in KB retrieval path; output uses reranked top results.

### P4.5 — Optional Next.js UI
- **Why:** Improve day-to-day operator ergonomics for runs and approvals.
- **What:** Delivered `apps/ui/` with incidents list, approvals list, and authenticated approve/reject actions against FastAPI.

### P4.6 — Expanded eval suite (20+)
- **Why:** Increase regression detection breadth across triage, citations, escalation, and injection safety.
- **What:** Expanded standard cases to 20 and extended scoring with citation-precision checks while preserving existing MoE gates.

### P4.7 — Post-incident loop
- **Why:** Convert operational incidents into durable process and quality improvements.
- **What:** Added postmortem template, operational runbook, and `python -m scripts.reindex_kb` helper to keep KB/evals synchronized after incidents.

### P4.8 — Model upgrade / shadow-testing rollout
- **Why:** Make model changes evidence-based, not ad hoc.
- **What:** Added dedicated workflow `.github/workflows/shadow-models.yml`, report persistence under `evals/reports/`, explicit pass/fail decision rules, and end-to-end process docs in `docs/shadow_models.md`.

---

## 4. Project state after hardening

### Operability
- New contributors can quickly understand architecture and extend MCP/evals with runbook support.
- Operators have both API and optional UI paths for incident/approval workflows.

### Quality and safety
- Eval coverage is broader and still deterministic in CI.
- Post-incident process enforces continuous learning (postmortem -> KB update -> eval case).
- Model promotions now require shadow evidence and explicit decision criteria.

### Governance
- Hardening transformed multiple one-off practices into documented, repeatable procedures.
- Board/task docs now reflect delivered status for P4 scope.

---

## 5. Definition of done (phase) — checklist

- [x] Architecture and extension docs (MCP/eval runbooks) are present and discoverable.
- [x] RAG retrieval quality hardening (reranker) is integrated.
- [x] Optional operator UI supports incident/approval operations with auth.
- [x] Eval suite expansion and citation-quality checks are implemented and CI-gated.
- [x] Post-incident loop is documented and executable.
- [x] Shadow model rollout workflow, reports, and promotion criteria are documented and runnable.
- [x] `BOARD.md` status is synchronized with task files.

---

*Hardening review — state at phase close. Update if additional P4 backports are merged or if hardening scope is reopened.*
