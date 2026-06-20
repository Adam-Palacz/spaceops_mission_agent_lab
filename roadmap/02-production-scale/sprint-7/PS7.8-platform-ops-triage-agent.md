# PS7.8 — Platform ops triage agent MVP (BL-005)

| Field | Value |
|-------|--------|
| **Task ID** | PS7.8 |
| **Status** | Done |
| **Backlog** | [BL-005](../../backlog/BL-005-ai-assisted-incident-triage.md) |

## Description

Read-only collector JSON (queue/DLQ/MCP health) + LLM hypotheses; **no** `--apply` without approval.
Runbook section in queue/DLQ docs.

**Domain:** platform/SRE (transport, DLQ, MCP breaker) — not mission telemetry triage.

## Deliverables

- [x] `apps/platform_ops/collector.py` — snapshot schema v1
- [x] `apps/platform_ops/triage.py` — rule-based hypotheses + optional LLM summary
- [x] `scripts/platform_ops_triage.py` — CLI (`--collect-only`, `--fixture`, safety gates)
- [x] Runbook §9 in [queue_dlq_recovery.md](../../../docs/runbooks/queue_dlq_recovery.md)
- [x] Fixtures + `tests/test_platform_ops_ps78.py`

## Acceptance

- [x] Deterministic fixture → stable JSON + top hypothesis class.
- [x] `--apply` blocked without `--i-approve`.
- [x] Recommendations list safe verify commands before approval-required remediate.
- [x] Audit block in report (timestamp, sources, suggested steps).

## Usage

```bash
python -m scripts.platform_ops_triage --collect-only
python -m scripts.platform_ops_triage --fixture tests/fixtures/platform_ops/dlq_backlog.json --no-llm
```
