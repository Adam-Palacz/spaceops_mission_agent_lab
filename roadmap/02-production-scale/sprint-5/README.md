# Production Scale — Sprint 5 (PS5)

**Goal:** complete LLM backend portability through a strict gateway, optional GPU backend, and
cost/safety controls so acceleration remains optional and reversible.

---

## Outcomes

- Unified gateway supports `openai` and optional `gpu` backend via feature flag.
- Health checks, circuit breaker, and fallback behavior for backend outages.
- Cost controls: idle TTL, scale-to-zero pattern, budget alert thresholds.
- Behavior parity checks between backends within defined tolerances.

---

## Tasks

See **[BOARD.md](BOARD.md)** for status of PS5.1-PS5.8.

---

## Definition of done (sprint)

- [ ] `LLM_BACKEND=openai|gpu` works through one gateway contract.
- [ ] GPU path can fail without breaking incident flow (safe fallback).
- [ ] Cost guardrails are documented and demonstrable.
- [ ] Backend parity evals exist and are repeatable.
