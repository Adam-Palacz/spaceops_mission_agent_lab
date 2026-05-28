# SpaceOps - local quality gates aligned with .github/workflows/ci.yml
#
# POSIX Make. On Windows, use Git Bash or WSL if `make` is unavailable.
# Override defaults, e.g.: `make test DATABASE_URL=postgresql://user:pass@host:5432/db`

PYTHON ?= python
PIP ?= $(PYTHON) -m pip
COMPOSE ?= docker compose -f infra/docker-compose.yml --project-directory .

# Match CI test job defaults (local Postgres must be up for `test` / `migrate-smoke`).
DATABASE_URL ?= postgresql://spaceops:spaceops@localhost:5432/spaceops
POSTGRES_PASSWORD ?= spaceops

.DEFAULT_GOAL := help

.PHONY: help install install-dev lint format typecheck check safety-gates semantic-check test migrate-smoke \
	golden-check golden-run golden-update compose-config docker-build gpu-up gpu-down gpu-smoke

help: ## Show this help (default goal)
	@echo SpaceOps Makefile - targets mirror CI where practical.
	@echo.
	@$(PYTHON) -c "import pathlib,re; lines=pathlib.Path('Makefile').read_text(encoding='utf-8').splitlines(); rows=[]; [rows.append((m.group(1),m.group(2))) for line in lines for m in [re.match(r'^([A-Za-z0-9_.-]+):.*?##\s*(.+)$$', line)] if m]; [print(f'  {name:<22} {desc}') for name, desc in sorted(rows)]"
	@echo.
	@echo Postgres-backed targets (test, migrate-smoke) use DATABASE_URL=$(DATABASE_URL)

install: ## pip install -r requirements.txt (upgrade pip first)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev: install ## Same as install (hook for future dev extras)

lint: ## ruff check . (same as CI lint job)
	ruff check .

format: ## ruff format . (project README / pre-commit)
	ruff format .

typecheck: ## mypy on apps.agent, apps.api, config, evals (same as CI)
	$(PYTHON) -m mypy -m apps.agent -m apps.api -m config -m evals --ignore-missing-imports

check: lint typecheck golden-check ## Fast pre-push gate: no Postgres required

safety-gates: ## PS4.7 hard gate: OPA/HITL/guardrails + ci gating tests (no Postgres)
	$(PYTHON) -m pytest tests/test_act_opa_policy.py tests/test_opa_client.py \
		tests/test_evidence_policy_ps41.py tests/test_prompt_injection_ps43.py \
		tests/test_guardrails_ps17.py tests/test_output_schema_ps42.py \
		tests/test_behavior_metrics_ps46.py tests/test_ci_gating_ps47.py -v

semantic-check: ## PS4.4 deterministic semantic evals (fixtures, no LLM)
	$(PYTHON) -m evals.semantic

test: ## pytest tests/ (needs Postgres; env matches CI test job)
	$(PYTHON) -c "import os,subprocess,sys; env=os.environ.copy(); env['DATABASE_URL']='$(DATABASE_URL)'; env['POSTGRES_PASSWORD']='$(POSTGRES_PASSWORD)'; sys.exit(subprocess.call(['pytest','tests/','-v'], env=env))"

migrate-smoke: ## alembic upgrade / downgrade / upgrade (needs Postgres)
	$(PYTHON) -c "import os,subprocess,sys; env=os.environ.copy(); env['DATABASE_URL']='$(DATABASE_URL)'; cmds=[['$(PYTHON)','-m','alembic','upgrade','head'],['$(PYTHON)','-m','alembic','downgrade','base'],['$(PYTHON)','-m','alembic','upgrade','head']]; rc=0; \
for cmd in cmds: \
    rc=subprocess.call(cmd, env=env); \
    (rc and sys.exit(rc)); \
print('Migration smoke passed')"

golden-check: ## Synthetic golden baseline - same as CI golden path (no live LLM)
	pytest tests/test_golden_baseline.py tests/test_golden_runner_ps45.py -v

# PS4.5: run fixture manifest + write diff report (no live LLM when using CI fixtures + mocks in tests).
golden-run: ## Golden runner on CI fixtures; writes data/replay/golden/reports/latest
	$(PYTHON) scripts/golden_runner.py run --manifest tests/fixtures/golden/manifest.json --baselines-dir tests/fixtures/golden/baselines --output-dir data/replay/golden/reports/latest

# Refresh data/replay/golden/baselines/run_<RUN_ID>_baseline.json after replay (needs env/MCP).
# Usage: make golden-update RUN_ID=<pipeline-run-uuid>
golden-update: ## Update golden baseline JSON for a run id (requires explicit confirm)
	$(PYTHON) scripts/golden_runner.py update --run-id "$(RUN_ID)" --confirm baseline-update

compose-config: ## Validate docker compose file interpolation (like CI docker-build job)
	$(PYTHON) -c "from pathlib import Path; import sys; ok=Path('.env').exists(); (not ok) and print('Missing .env - copy .env.example to .env for compose interpolation.'); sys.exit(0 if ok else 1)"
	$(COMPOSE) config >/dev/null

docker-build: ## Build api, ui, MCP images (compose profile; like CI)
	$(PYTHON) -c "from pathlib import Path; import sys; ok=Path('.env').exists(); (not ok) and print('Missing .env - copy .env.example to .env'); sys.exit(0 if ok else 1)"
	$(COMPOSE) --profile ui build api ui telemetry-mcp kb-mcp ticket-mcp gitops-mcp

gpu-up: ## PS5.3 Start NIM (profile gpu), wait for health, optional API with gpu profile
	@$(PYTHON) -c "from pathlib import Path; Path('var').mkdir(parents=True, exist_ok=True)"
	$(COMPOSE) --profile gpu up -d nim-llm
	$(PYTHON) scripts/llm_gpu_smoke.py --wait-health --timeout 600
	@echo "NIM is up on http://localhost:8005 — set LLM_BACKEND=gpu in .env for host runs."

gpu-down: ## PS5.3 Stop NIM container
	$(COMPOSE) --profile gpu stop nim-llm

gpu-smoke: ## PS5.3 Health + generate on host (requires LLM_BACKEND=gpu in .env)
	$(PYTHON) scripts/llm_gpu_smoke.py --health-only --generate
