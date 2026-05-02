# Production Scale — Sprint 5 (PS5)

**Goal:** complete LLM backend portability through a strict gateway, optional GPU backend, and
cost/safety controls so acceleration remains optional and reversible.

---

## Outcomes

- Unified gateway supports `openai` and optional `gpu` backend via feature flag.
- Health checks, circuit breaker, and fallback behavior for backend outages.
- Cost controls: idle TTL, scale-to-zero pattern, budget alert thresholds.
- Behavior parity checks between backends within defined tolerances.
- **Observability for evals (optional):** LangSmith, MLflow, or similar — **does not replace**
  deterministic YAML gates; extends PS4.4 / PS5.8 for **trend** and prompt-regression signals (see
  [phase README cross-cutting](../README.md#cross-cutting-durability-safety-and-evals)).

---

## Tasks

See **[BOARD.md](BOARD.md)** for status of PS5.1-PS5.8.

---

## Definition of done (sprint)

- [ ] `LLM_BACKEND=openai|gpu` works through one gateway contract.
- [ ] GPU path can fail without breaking incident flow (safe fallback).
- [ ] Cost guardrails are documented and demonstrable.
- [ ] Backend parity evals exist and are repeatable.
- [ ] **PS5.8** documents how optional tracing/eval SaaS connects to CI (nightly vs merge gate).
