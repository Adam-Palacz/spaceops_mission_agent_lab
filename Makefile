# Conveniences (POSIX Make). On Windows, use Git Bash or WSL if `make` is unavailable.

.PHONY: golden-check golden-update

# Synthetic golden baseline — same checks as CI (no live LLM).
golden-check:
	pytest tests/test_golden_baseline.py -v

# Refresh data/replay/golden/baselines/run_<RUN_ID>_baseline.json after replay (needs env/MCP).
# Usage: make golden-update RUN_ID=<pipeline-run-uuid>
golden-update:
	python scripts/golden_baseline.py update --run-id "$(RUN_ID)"
