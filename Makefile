# SpaceOps - local quality gates aligned with .github/workflows/ci.yml
#
# POSIX Make. On Windows, GnuWin32 make works; prefer .venv Python (see below).
# Override defaults, e.g.: `make test DATABASE_URL=postgresql://user:pass@host:5432/db`

ifeq ($(OS),Windows_NT)
VENV_PY := .venv\Scripts\python.exe
ifneq ($(wildcard $(VENV_PY)),)
PYTHON ?= .venv/Scripts/python.exe
else
PYTHON ?= py -3
endif
PYTHON_RUN := "$(PYTHON)"
else
PYTHON ?= python3
PYTHON_RUN := $(PYTHON)
endif

PIP ?= $(PYTHON_RUN) -m pip
COMPOSE ?= docker compose -f infra/docker-compose.yml --project-directory .

# Match CI test job defaults (local Postgres must be up for `test` / `migrate-smoke`).
DATABASE_URL ?= postgresql://spaceops:spaceops@localhost:5432/spaceops
POSTGRES_PASSWORD ?= spaceops

.DEFAULT_GOAL := help

.PHONY: help install install-dev lint format typecheck check safety-gates semantic-check test migrate-smoke \
	golden-check golden-run golden-update compose-config docker-build gpu-up gpu-down gpu-smoke gpu-idle-check \
	gpu-idle-integration backend-parity-check helm-template helm-lint k8s-up k8s-down k8s-status k8s-smoke \
	k8s-rollout-demo k8s-isolation-verify k8s-secrets-bootstrap gitops-install gitops-bootstrap \
	gitops-status gitops-rollout-demo

help: ## Show this help (default goal)
	@echo SpaceOps Makefile - targets mirror CI where practical.
	@$(PYTHON_RUN) -c "print()"
	@$(PYTHON_RUN) -c "import pathlib,re; lines=pathlib.Path('Makefile').read_text(encoding='utf-8').splitlines(); rows=[]; [rows.append((m.group(1),m.group(2))) for line in lines for m in [re.match(r'^([A-Za-z0-9_.-]+):.*?##\s*(.+)$$', line)] if m]; [print(f'  {name:<22} {desc}') for name, desc in sorted(rows)]"
	@$(PYTHON_RUN) -c "print()"
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
	$(PYTHON_RUN) -m mypy -m apps.agent -m apps.api -m config -m evals --ignore-missing-imports

check: lint typecheck golden-check ## Fast pre-push gate: no Postgres required

safety-gates: ## PS4.7 hard gate: OPA/HITL/guardrails + ci gating tests (no Postgres)
	$(PYTHON_RUN) -m pytest tests/test_act_opa_policy.py tests/test_opa_client.py \
		tests/test_evidence_policy_ps41.py tests/test_prompt_injection_ps43.py \
		tests/test_guardrails_ps17.py tests/test_output_schema_ps42.py \
		tests/test_behavior_metrics_ps46.py tests/test_ci_gating_ps47.py -v

semantic-check: ## PS4.4 deterministic semantic evals (fixtures, no LLM)
	$(PYTHON_RUN) -m evals.semantic

test: ## pytest tests/ (needs Postgres; env matches CI test job)
	$(PYTHON_RUN) -c "import os,subprocess,sys; env=os.environ.copy(); env['DATABASE_URL']='$(DATABASE_URL)'; env['POSTGRES_PASSWORD']='$(POSTGRES_PASSWORD)'; sys.exit(subprocess.call(['pytest','tests/','-v'], env=env))"

migrate-smoke: ## alembic upgrade / downgrade / upgrade (needs Postgres)
	$(PYTHON_RUN) -c "import os,subprocess,sys; env=os.environ.copy(); env['DATABASE_URL']='$(DATABASE_URL)'; cmds=[['$(PYTHON)','-m','alembic','upgrade','head'],['$(PYTHON)','-m','alembic','downgrade','base'],['$(PYTHON)','-m','alembic','upgrade','head']]; rc=0; \
for cmd in cmds: \
    rc=subprocess.call(cmd, env=env); \
    (rc and sys.exit(rc)); \
print('Migration smoke passed')"

golden-check: ## Synthetic golden baseline - same as CI golden path (no live LLM)
	pytest tests/test_golden_baseline.py tests/test_golden_runner_ps45.py -v

# PS4.5: run fixture manifest + write diff report (no live LLM when using CI fixtures + mocks in tests).
golden-run: ## Golden runner on CI fixtures; writes data/replay/golden/reports/latest
	$(PYTHON_RUN) scripts/golden_runner.py run --manifest tests/fixtures/golden/manifest.json --baselines-dir tests/fixtures/golden/baselines --output-dir data/replay/golden/reports/latest

# Refresh data/replay/golden/baselines/run_<RUN_ID>_baseline.json after replay (needs env/MCP).
# Usage: make golden-update RUN_ID=<pipeline-run-uuid>
golden-update: ## Update golden baseline JSON for a run id (requires explicit confirm)
	$(PYTHON_RUN) scripts/golden_runner.py update --run-id "$(RUN_ID)" --confirm baseline-update

compose-config: ## Validate docker compose file interpolation (like CI docker-build job)
	$(PYTHON_RUN) -c "from pathlib import Path; import sys; ok=Path('.env').exists(); (not ok) and print('Missing .env - copy .env.example to .env for compose interpolation.'); sys.exit(0 if ok else 1)"
	$(COMPOSE) config >/dev/null

docker-build: ## Build api, ui, MCP images (compose profile; like CI)
	$(PYTHON_RUN) -c "from pathlib import Path; import sys; ok=Path('.env').exists(); (not ok) and print('Missing .env - copy .env.example to .env'); sys.exit(0 if ok else 1)"
	$(COMPOSE) --profile ui build api ui telemetry-mcp kb-mcp ticket-mcp gitops-mcp

gpu-up: ## PS5.3 Start NIM (profile gpu), wait for health, optional API with gpu profile
	@$(PYTHON_RUN) -c "from pathlib import Path; Path('var').mkdir(parents=True, exist_ok=True)"
	$(COMPOSE) --profile gpu up -d nim-llm
	$(PYTHON_RUN) scripts/llm_gpu_smoke.py --wait-health --timeout 600
	@echo "NIM is up on http://localhost:8005 — set LLM_BACKEND=gpu in .env for host runs."

gpu-down: ## PS5.3 Stop NIM container
	$(COMPOSE) --profile gpu stop nim-llm

gpu-smoke: ## PS5.3 Health + generate on host (requires LLM_BACKEND=gpu in .env)
	$(PYTHON_RUN) scripts/llm_gpu_smoke.py --health-only --generate

gpu-idle-check: ## PS5.7 Dry-run idle TTL decision (no container stop)
	$(PYTHON_RUN) scripts/gpu_idle_shutdown.py --dry-run

gpu-idle-integration: ## PS5.7 Real compose/API GPU activity acceptance (requires GPU/NIM)
	$(PYTHON_RUN) -c "from pathlib import Path; import sys; ok=Path('.env').exists(); (not ok) and print('Missing .env - copy .env.example to .env and set LLM_BACKEND=gpu / NGC_API_KEY.'); sys.exit(0 if ok else 1)"
	@$(PYTHON_RUN) -c "from pathlib import Path; Path('var').mkdir(parents=True, exist_ok=True)"
	$(COMPOSE) --profile gpu up -d nim-llm api
	$(PYTHON_RUN) scripts/gpu_activity_integration.py

backend-parity-check: ## PS5.8 Fixture parity tests (no live LLM)
	pytest tests/test_backend_parity_ps58.py -v

HELM_CHART := deploy/helm/spaceops

helm-lint: ## PS6.2 Validate Helm chart (requires helm CLI)
	helm lint $(HELM_CHART) -f $(HELM_CHART)/values.yaml

helm-template: ## PS6.2 Render minimal dev manifests to stdout
	helm template spaceops $(HELM_CHART) \
		-f $(HELM_CHART)/values.yaml \
		-f $(HELM_CHART)/values-dev.yaml \
		-f $(HELM_CHART)/values-minimal-dev.yaml \
		--set secrets.postgresPassword=local-dev-only

# PS6.3 — local kind cluster (requires docker, kind, kubectl, helm on PATH).
K8S_SKIP_BUILD ?= 0
K8S_SKIP_CALICO ?= 0
K8S_ISOLATION_ARGS ?=

k8s-up: ## PS6.3 Create kind cluster + Helm install minimal dev profile
	$(PYTHON_RUN) scripts/k8s_local.py up $(if $(filter 1 true yes,$(K8S_SKIP_BUILD)),--skip-build,) $(if $(filter 1 true yes,$(K8S_SKIP_CALICO)),--skip-calico,)

k8s-down: ## PS6.3 Helm uninstall + delete kind cluster spaceops-dev
	$(PYTHON_RUN) scripts/k8s_local.py down

k8s-status: ## PS6.3 Show pods/services and Helm release in spaceops-dev
	$(PYTHON_RUN) scripts/k8s_local.py status

k8s-smoke: ## PS6.3 Port-forward API and GET /health
	$(PYTHON_RUN) scripts/k8s_local.py smoke

k8s-rollout-demo: ## PS6.4 Helm upgrade + rollback demo (requires make k8s-up)
	$(PYTHON_RUN) scripts/k8s_rollout_demo.py

k8s-isolation-verify: ## PS6.5 Verify NetworkPolicy, quota, RBAC on local cluster
	$(PYTHON_RUN) scripts/k8s_isolation_verify.py $(K8S_ISOLATION_ARGS)

k8s-secrets-bootstrap: ## PS6.6 Create/update K8s Secret from env (K8S_POSTGRES_PASSWORD, OPENAI_API_KEY, …)
	$(PYTHON_RUN) scripts/k8s_secrets_bootstrap.py --create-namespace

# PS6.7 — optional Argo CD GitOps (requires Git remote + pushed deploy/gitops/).
GITOPS_BOOTSTRAP_ARGS ?=

gitops-install: ## PS6.7 Install Argo CD controller in namespace argocd
	$(PYTHON_RUN) scripts/gitops_bootstrap.py install --wait

gitops-bootstrap: ## PS6.7 Apply AppProject + app-of-apps (set GITOPS_REPO_URL if needed)
	$(PYTHON_RUN) scripts/gitops_bootstrap.py bootstrap $(GITOPS_BOOTSTRAP_ARGS)

gitops-status: ## PS6.7 Show Argo CD Application status
	$(PYTHON_RUN) scripts/gitops_bootstrap.py status

GITOPS_DEMO_ARGS ?=

gitops-rollout-demo: ## PS6.7 GitOps sync demo (use GITOPS_DEMO_ARGS=--sync-only after git push)
	$(PYTHON_RUN) scripts/gitops_rollout_demo.py $(GITOPS_DEMO_ARGS)
