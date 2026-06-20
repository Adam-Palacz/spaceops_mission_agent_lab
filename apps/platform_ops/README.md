# Platform ops triage (PS7.8)

Read-only **platform/SRE** incident helper — separate from the mission agent (satellite anomaly triage).

| Module | Role |
|--------|------|
| `collector.py` | Gather queue/DLQ/MCP/circuit evidence as JSON |
| `triage.py` | Rule-based hypotheses + optional LLM summary |

CLI: `python -m scripts.platform_ops_triage` · Runbook: [docs/runbooks/queue_dlq_recovery.md](../../docs/runbooks/queue_dlq_recovery.md) §9.
