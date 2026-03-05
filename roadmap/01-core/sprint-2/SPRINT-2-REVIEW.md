## Sprint 2 — Review

**Sprint:** 01-core, Sprint 2 (Act, approvals, OPA, injection suite, dashboards)  
**Scope:** S2.1–S2.11  
**Status:** All Sprint 2 tasks functionally delivered; BOARD updated to Done where applicable.

---

## 1. Executive summary

Sprint 2 delivered the **Act** phase on top of the existing pipeline: the agent can now propose and (after human approval) execute changes via Ticketing and GitOps, guarded by OPA and an authenticated, idempotent approval API. OPA is wired in fail-closed mode so policy errors, timeouts, or outages never result in silent execution; unsafe or off-policy plans are further constrained by an injection eval suite that enforces **unsafe-action rate = 0**. Prometheus metrics and a Grafana dashboard provide basic production-style observability (run count, latency, errors, tool calls), and pytest-level unit tests for OPA client, Act behaviour, approval API, and audit logging make the new surface area regression-safe. **Sprint goal achieved.**

---

## 2. Sprint goal and assessment

**Goal (from sprint-2 README):**  
*Safe actions execute (ticket + GitOps PR); restricted require OPA allow + approval; approval API is idempotent and authenticated; fail-closed on OPA failure; injection suite + dashboards prove safety and observability.*

| Criterion | Status | Notes |
|-----------|--------|-------|
| Safe actions create ticket and config change | ✅ | Act node maps `create_ticket` / `create_pr` steps to MCP Ticketing and GitOps; ticket NDJSON and ops-config subtree used as targets. |
| Restricted actions go through OPA + approval | ✅ | Decide tags steps as safe/restricted; Act calls `opa_allow` for restricted steps and only creates approval requests on allow. |
| OPA fail-closed (NF8) | ✅ | `opa_allow()` returns False on timeout, connection error, 5xx, malformed/empty response; Act treats this as deny and escalates with `policy_deny`. |
| Approval endpoints idempotent and authenticated | ✅ | `GET /approvals` and `POST /approvals/:id/approve|reject` use API key; second approve returns 200 without re-execution. |
| Audit of human approvals (NF9) | ✅ | Approval decisions append audit entries with `actor="human"`, decision, outcome, and correlation to approval id. |
| Injection suite with unsafe-action rate = 0 | ✅ | `evals/injection_suite` + `unsafe_action_performed()` in `evals/scoring.py`; CI evals fail on any unsafe step. |
| Metrics + dashboard | ✅ | `/metrics` Prometheus endpoint, Prometheus+Grafana in `infra/docker-compose.yml`, dashboard for runs, latency, errors, tool calls. |
| Unit tests for S2 surface (tests/) | ✅ | `tests/test_api.py`, `tests/test_opa_client.py`, `tests/test_act_opa_policy.py`, `tests/test_audit_log.py`, `tests/test_evals.py` cover approval API, OPA client, Act, audit, and injection logic. |

**Verdict:** Sprint 2 **goal achieved**.

---

## 3. What was done — task by task

### S2.1 — ops-config repo / subtree
- **Why:** Provide a concrete GitOps target for config changes (thresholds, channel lists) without requiring a separate repo yet.
- **What:** Added `ops-config/` subtree with sample YAML (`alerts/thresholds.yaml`, `channels/channel_list.yaml`) and README describing how GitOps MCP targets it. Root README documents the location and future split to a dedicated repo if needed.

### S2.2 — MCP Ticketing + MCP GitOps
- **Why:** Implement safe, automatable endpoints for incident follow-up (tickets) and configuration changes (PRs) that Act can orchestrate.
- **What:** MCP Ticketing server with `create_ticket(title, body)` appends to `data/incidents/tickets.ndjson`; MCP GitOps server with `create_pr(repo_path, branch, files)` writes/updates files under `ops-config/` and returns a summary that can later back a real PR. Environment variables in `config`/`.env.example` prepare integration with GitHub but remote PR creation can be layered on in a later sprint.

### S2.3 — Decide (safe/restricted) + Act
- **Why:** Separate **planning** (what to do) from **execution** (what can be done automatically vs requires approval), and keep everything citation-grounded.
- **What:** Decide now emits structured steps including `safe` flag and `action_type` (`create_ticket`, `create_pr`, `change_config`, `report`). Act loops over steps: safe ones call Ticketing/GitOps MCPs immediately; restricted ones call OPA first and, on allow, create approval requests instead of executing. OPA deny/error causes escalation with `reason="policy_deny"`, and audit entries are written for each OPA check and tool call.

### S2.4 — OPA: allowlist + fail-closed
- **Why:** Enforce a central, reviewable policy for which tools/arguments are allowed and guarantee fail-closed semantics when policy evaluation is not available.
- **What:** OPA service and Rego policy (`infra/opa/agent_policy.rego`) define an allowlist of tools and argument constraints (e.g. denying "restart all"). `apps.agent.opa_client.opa_allow()` posts incident/step input to OPA and interprets results strictly: only a boolean `true` result counts as allow. All other cases (false, error, timeout, HTTP 5xx, malformed/empty JSON) are treated as deny; Act reads this and escalates instead of executing.

### S2.5 — Approval API (idempotent, auth)
- **Why:** Give humans explicit control over restricted actions with a clear API, while keeping calls auditable and resistant to accidental double-execution.
- **What:** Approval storage in `apps.agent.approval_store` (JSON files under `data/approvals/` or configured path); API endpoints `GET /approvals`, `POST /approvals/:id/approve`, `POST /approvals/:id/reject` guarded by `APPROVAL_API_KEY` (header `X-API-Key` or Bearer token). Approve/reject update status and write audit entries with `actor="human"`, decision, outcome, and identity. Approve is idempotent: repeat calls on the same id return 200 without re-running execution.

### S2.6 — Execute restricted action on approve
- **Why:** Close the loop from plan → approval → execution for restricted changes (e.g. config tweaks via GitOps), while keeping behaviour predictable and observable.
- **What:** Approval approve handler loads the stored request and, if it was pending, calls `approval_executor.execute_approved_action()` which maps `action_type` (e.g. `change_config`, `restart_service`) to GitOps MCP or a no-op. Execution runs once per approval id; outcomes (success or failure) are written to audit with `actor="agent"` and returned in the API response. Re-approving an already-approved id does not trigger execution again.

### S2.7 — Audit log: approval events
- **Why:** Satisfy NF9 / compliance: demonstrate who approved or rejected what, when, and with which outcome.
- **What:** Approval API now appends audit entries for every approve/reject with `actor="human"`, decision (`approve`/`reject`), policy_result (`"n/a"`), outcome (`success`), and a reference to the approval request (id/args). The approval store records `decided_at`/`decided_by`, and tests verify at least two human entries (approve + reject) with the required schema and decisions.

### S2.8 — Injection suite
- **Why:** Defend against prompt injection / unsafe instructions by validating that the agent never performs clearly unsafe actions, even when runbooks try to coerce it.
- **What:** `evals/injection_suite/` contains 5–10 markdown docs with adversarial instructions (ignore OPA, run shell, skip approval, restart all, etc.), and `evals/injection_cases.yaml` runs the pipeline with these docs prepended to the payload. `evals.scoring` defines `ALLOWED_ACTION_TYPES` and `UNSAFE_PHRASES`, and `unsafe_action_performed()` flags any forbidden tool or phrase in plan/approval steps. Injection cases are integrated into `python -m evals.scoring`, and CI fails if any unsafe action is produced.

### S2.9 — Prometheus metrics + Grafana dashboard
- **Why:** Provide basic production-style observability for runs, latency, errors, and tool usage.
- **What:** API exposes `/metrics` with Prometheus counters/histograms (`agent_runs_total`, `agent_run_duration_seconds`, `agent_errors_total`, `agent_tool_calls_per_run`). `infra/docker-compose.yml` adds Prometheus (scraping the API on `host.docker.internal:8000`) and Grafana with a pre-wired Prometheus datasource and dashboard showing run count, latency distribution, error rate, and tool-call metrics. Running the stack and a few `/runs` calls produces visible data in Grafana.

### S2.10 — OPA unit tests
- **Why:** Make OPA policy and client behaviour regression-safe and transparent.
- **What:** Unit tests in `tests/test_opa_client.py` and `tests/test_act_opa_policy.py` cover allow/deny, forbidden phrases like "restart all", and fail-closed behaviour (timeouts, connection errors, HTTP 5xx, malformed/empty results). An optional integration test hits the real OPA HTTP API when `OPA_POLICY_INTEGRATION=1` and OPA is running, ensuring the Rego bundle denies unsafe patterns. Act tests assert that deny paths cause escalation instead of approval creation.

### S2.11 — Unit tests in tests/
- **Why:** Lock in Sprint 2 semantics (approval API, OPA client, Act) via fast, deterministic pytest coverage.
- **What:** Existing tests (`tests/test_api.py`, `tests/test_opa_client.py`, `tests/test_act_opa_policy.py`, `tests/test_audit_log.py`, `tests/test_evals.py`) already covered Sprint 2 scope; S2.11 formalised this coverage in roadmap docs and tightened test infra. `tests/conftest.py` now routes audit/approvals to a temp dir so pytest does not modify tracked `data/` files, and the long-running `test_scoring_module_runs_and_outputs_score` is skipped by default in pre-commit unless `RUN_EVALS_SCORING=1` is set, keeping hooks fast while CI can still exercise full evals.

---

## 4. Project state after Sprint 2

### How to run (Act-enabled stack)
1. **Environment:** `pip install -r requirements.txt`, `.env` with `OPENAI_API_KEY`, `APPROVAL_API_KEY`, and optionally Postgres / OTel / GitHub tokens.
2. **Stack:** `docker compose -f infra/docker-compose.yml up -d` (Postgres, OTel Collector, Jaeger, Prometheus, Grafana, OPA).
3. **API:** `python -m apps.api.main` → `http://localhost:8000` (health, ingest, runs, approvals, metrics).
4. **Agent:** `POST /runs` or `python -m apps.agent.run` to generate plans including safe/restricted steps; safe actions call Ticketing/GitOps MCPs; restricted actions generate approval requests gated by OPA and the approval API.
5. **Observability:** Jaeger for traces, `/metrics` + Prometheus/Grafana for metrics, audit NDJSON for immutable action history.

### What works
- **Act:** Safe steps can create tickets and GitOps-ready config changes; restricted steps follow OPA → approval → execution flow, with fail-closed handling.
- **Approvals:** Authenticated, idempotent approval endpoints that record human decisions and link them to executed actions.
- **OPA policy:** Central allowlist and argument checks that deny obviously unsafe actions and integrate with Act escalation paths.
- **Safety evals:** Standard evals plus injection suite run via `python -m evals.scoring`, enforcing 0 unsafe actions.
- **Metrics and dashboards:** Basic but useful views into run volume, latency, errors, and tool usage.
- **Tests:** `pytest tests/` (with project deps installed) covers core S2 logic; CI continues to run ruff, mypy, pytest, and evals.

---

## 5. Requirements coverage (goals) in Sprint 2

| ID | Requirement | S2 | Notes |
|----|-------------|----|-------|
| F4 | Decide plan (safe vs restricted) | ✅ | Decide annotates steps with `safe` and `action_type`; used by Act. |
| F5 | Act safe actions automatically | ✅ | Ticketing/GitOps MCPs called directly for safe steps. |
| F6 | Act restricted via OPA + approvals | ✅ | Restricted steps require OPA allow + approval API before execution. |
| F8 | Approval API | ✅ | Authenticated, idempotent, with audit and storage. |
| NF1 | No shell/exec, only MCP | ✅ | Injection suite and OPA policy guard against shell/exec-like actions. |
| NF3 | Policy enforcement | ✅ | OPA allowlist + argument validation wired into Act. |
| NF4 | Evals in CI (incl. injection) | ✅ | `evals/scoring.py` runs standard + injection cases; CI uses it as a gate. |
| NF8 | Fail-closed on OPA failure | ✅ | Any OPA failure/timeout leads to deny and escalation; no execution. |
| NF9 | Audit of approvals | ✅ | Human decisions recorded with identity and outcome; append-only audit. |

---

## 6. Definition of done (sprint) — checklist

- [x] Safe actions create ticket and config changes via MCP; restricted actions go through OPA + approval → execution.
- [x] Approval API is authenticated, idempotent, and writes human decisions to the audit log.
- [x] OPA client and Act enforce fail-closed behaviour (no silent execution on policy failure).
- [x] Injection suite enforces unsafe-action rate = 0 in evals.
- [x] Metrics and dashboard expose run volume, latency, errors, and tool-call behaviour.
- [x] Unit tests in `tests/` cover approval API, OPA client, Act, and audit semantics; pytest runs in CI.

---

*Sprint 2 review — state at sprint close. Update only if scope for 01-core Sprint 2 changes or new S2 work is backported.*

