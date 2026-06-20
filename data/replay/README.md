# Replay and golden-run artifacts

Deterministic replay inputs and **golden baselines** for CI and PS3/PS4 quality gates.

| Subfolder | Purpose |
|-----------|---------|
| **baselines/** | Pinned replay snapshots (e.g. burst scenarios). |
| **golden/** | Golden manifest + expected outcomes for regression checks. |
| **runs/** | Ephemeral replay run output (gitignored). |

Docs: [docs/golden_run_baselines.md](../../docs/golden_run_baselines.md) ·
[docs/runbooks/replay_workflow.md](../../docs/runbooks/replay_workflow.md).
