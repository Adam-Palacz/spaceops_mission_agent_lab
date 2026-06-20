# Multi-cloud burst routing runbook (PS7.7)

Simulation and audit for optional **cloud B burst inference** — no live second cluster required.

## When to use

- Planning Phase 7 Stage 4 burst capacity
- Verifying policy + kill-switch before pointing `GPU_LLM_BASE_URL` at an external endpoint
- Reviewing `backend_routing_reason` in gateway logs after a run

## Simulation (local)

```bash
python scripts/simulate_multicloud_burst_routing.py
python scripts/simulate_multicloud_burst_routing.py --json
```

Exit code **0** when all scenarios match expected `backend_routing_reason` values.

Policy module: `apps/llm_burst_routing.py` · ADR: [0010-multicloud-burst-routing.md](../adr/0010-multicloud-burst-routing.md).

## Env flags (audit / future live burst)

| Env | Default | Role |
|-----|---------|------|
| `LLM_BURST_ENABLED` | `false` | Policy simulation considers burst path |
| `LLM_BURST_KILL_SWITCH` | `false` | Force primary; audit `kill_switch_active` |
| `LLM_BURST_BACKEND` | `gpu` | Burst backend id (cloud B stand-in) |
| `LLM_BURST_LATENCY_SLA_MS` | `2000` | p95 latency gate for burst |
| `LLM_BURST_ROUTING_AUDIT` | `true` | Attach `backend_routing_reason` on gateway calls |

Live routing to cloud B is **not** enabled in PS7.7 — flags affect audit and simulation only until Phase 7.

## Kill-switch drill

1. Set `LLM_BURST_KILL_SWITCH=true` on API Deployment (Helm `api.extraEnv` or emergency patch).
2. Trigger `POST /runs` — gateway logs should include `backend_routing_reason=kill_switch_active`.
3. Clear flag and roll out.

## Fallback expectations

| Condition | Expected behavior |
|-----------|-------------------|
| Burst unhealthy | Primary backend; reason `burst_unavailable` in simulation |
| Budget exceeded | `LLMBudgetExceededError`; no backend fallback (PS5.6) |
| GPU timeout/error | OpenAI fallback; `backend_routing_reason=fallback:gpu_timeout` etc. |

## Related

- [llm_gateway.md](../llm_gateway.md) — gateway contract
- [llm_cost_guardrails.md](../llm_cost_guardrails.md) — budget modes
- [environment_promotion.md](environment_promotion.md) — promotion gates
