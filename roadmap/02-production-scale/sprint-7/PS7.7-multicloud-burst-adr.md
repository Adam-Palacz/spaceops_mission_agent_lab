# PS7.7 — Multi-cloud burst ADR (BL-004)

| Field | Value |
|-------|--------|
| **Task ID** | PS7.7 |
| **Status** | Done |
| **Backlog** | [BL-004](../../backlog/BL-004-smart-resource-management-multicloud-burst.md) |

## Description

ADR + simulation for GPU burst routing to cloud B: kill-switch, audit `backend_routing_reason`.
**No live multi-cloud** in PS7.7 — policy proof only.

## Deliverables

- [x] [ADR 0010](../../../docs/adr/0010-multicloud-burst-routing.md)
- [x] `apps/llm_burst_routing.py` — deterministic policy
- [x] `scripts/simulate_multicloud_burst_routing.py`
- [x] Gateway + provenance `backend_routing_reason`
- [x] [multicloud_burst_routing.md](../../../docs/runbooks/multicloud_burst_routing.md)
- [x] `tests/test_multicloud_burst_ps77.py`

## Acceptance

- [x] Simulation: same policy inputs → same routing reason.
- [x] Burst unavailable → primary fallback in policy (no unsafe Act).
- [x] Audit field on gateway calls.
- [x] Kill-switch documented and tested.

## References

- Phase 7 Stage 4: [02-production-scale.md](../../02-production-scale.md)
