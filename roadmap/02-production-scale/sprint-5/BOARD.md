# PS5 — Board

| Task | Title | Status | Notes |
|------|-------|--------|-------|
| PS5.1 | Gateway backend abstraction hardening | Todo | Ensure all model calls go through one interface. |
| PS5.2 | OpenAI backend adapter parity tests | Todo | Baseline behavior and metadata logging. |
| PS5.3 | Optional GPU backend adapter | Todo | NIM/Triton-compatible adapter behind same contract. |
| PS5.4 | Backend healthcheck + circuit breaker | Todo | Automatic fallback on unhealthy GPU backend. |
| PS5.5 | Backend feature flags and rollout policy | Todo | Runtime toggle + safe default behavior. |
| PS5.6 | Cost telemetry and guardrails | Todo | Token/spend metadata + threshold alerts. |
| PS5.7 | Idle TTL and scale-to-zero workflow | Todo | Auto shutdown scripts/profile behavior. |
| PS5.8 | Parity eval suite and tolerance definition | Todo | Compare quality/latency bands; **optional LangSmith/MLflow** export for trends (with PS4.7 gate policy). |

**Status key:** Todo | In progress | Done | Blocked
