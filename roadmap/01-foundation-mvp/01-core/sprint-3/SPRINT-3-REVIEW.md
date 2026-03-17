## Sprint 3 — Review

**Sprint:** 01-core, Sprint 3 (observability, model lifecycle, resilience, ops process)  
**Scope:** S3.0–S3.8 (with S3.1 intentionally deferred/left open for a later hardening phase).  
**Status:** All planned Sprint 3 “spine” / resilience / process tasks delivered; S3.1 remains Todo by design.

---

## 1. Executive summary

Sprint 3 moved the lab from a “working agent” to a more **observable, resilient, and governable** system. A lightweight LLM observability spine was added to capture runs and calls in a Langfuse-compatible way; prompts were centralised in a versioned registry; model lifecycle hooks for shadow-testing were introduced; and context-compaction guards the agent’s memory footprint. On the resilience side, HTTP/MCP calls now have retries with jitter and a circuit breaker, and a chaos/degradation harness exercises failure modes (MCP slow/unavailable, OPA down) to ensure the agent escalates or fails closed instead of hanging. Finally, Dependabot-based automated dependency updates, a secrets abstraction, and a documented tech-debt budget make ongoing maintenance and security **part of the process**, not an afterthought. The injection suite still passes with unsafe-action rate = 0, and evals are treated as gates for dependency PRs. **Sprint goal achieved for S3.0, S3.2–S3.8; S3.1 is prepared but not yet executed in full.**

---

## 2. Sprint goal and assessment

**Goal (informal for Sprint 3):**  
*Add observability and lifecycle “spine” around the agent (LLM observability, prompt registry, model upgrade hooks, context compaction), harden external interactions (retry/circuit breaker, chaos harness), and introduce process guardrails (automated dependency updates, secrets plan, tech-debt budget) without breaking existing eval guarantees.*

| Criterion | Status | Notes |
|-----------|--------|-------|
| LLM observability spine in place | ✅ | `apps/llm_observability.py` logs runs and calls (NDJSON + OTel span attrs) with `run_id`, `node`, `model_id`, `prompt_id`, `prompt_version`, eval IDs. |
| Prompts centralised and versioned | ✅ | `prompts/registry.py` holds triage/decide prompts with IDs and versions; nodes reference them instead of inline strings. |
| Model lifecycle / shadow-testing hooks | ⚠️ | Abstraction and script in place (`apps/model_selection.py`, `evals/shadow_models.py`), but S3.1 work (running full shadow evals and acting on them) is still Todo by choice. |
| Context window compaction | ✅ | `compact_history` + `_wrap_node` enforce caps on hypotheses/citations after each node. |
| HTTP/MCP retry + circuit breaker | ✅ | `apps/common/http_resilience.py` wraps OPA + MCP, with retries on transient errors and per-key circuits that fail closed when open. |
| Chaos / degradation harness | ✅ | `tests/test_chaos_degradation.py` scenarios simulate MCP/OPA failures and assert escalation/fail-closed behaviour. |
| Automated dependency updates | ✅ | `.github/dependabot.yml` for pip + Actions; CI runs ruff, mypy, pytest, evals on Dependabot PRs. |
| Secrets management abstraction + plan | ✅ | `apps/common/secrets.py` + `get_secret()` in `config.py` for key secrets; `docs/secrets.md` documents backend/migration path. |
| Tech-debt budget process | ✅ | `docs/process.md` codifies the ~20% tech-debt rule; Sprint 3 tasks S3.4–S3.8 are tagged as debt examples. |
| Injection suite and evals still enforce unsafe=0 | ✅ | `python -m evals.scoring` passes all injection cases; standard cases only fail when MCP isn’t running locally (CI uses Telemetry MCP). |

**Verdict:** Sprint 3 **goal achieved** for observability, resilience, and process. S3.1 remains as a follow-on for a dedicated model-upgrade sprint.

---

## 3. What was done — task by task

### S3.0 — LLM observability spine (Langfuse-compatible)
- **Why:** Make LLM behaviour inspectable and comparable across runs/models without deploying a full Langfuse stack.
- **What:** `apps/llm_observability.py` exposes `start_llm_run` and `log_llm_call` that write NDJSON under `data/llm_runs/` and attach attributes to OTel spans. `triage`, `decide`, and evals now call into this spine with `run_id`, `node`, `model_id`, `prompt_id`, `prompt_version`, and eval/injection case IDs, enabling offline analysis and compatibility with Langfuse-style tooling later.

### S3.2 — Prompt registry & versioning
- **Why:** Avoid prompt drift and magic strings; make it possible to audit which prompt version produced which behaviour.
- **What:** `prompts/registry.py` defines a `Prompt` dataclass and a registry keyed by ID (`triage`, `decide`), including `version` and description. Agent nodes fetch prompts via `get_prompt(...)`, and observability logs include `prompt_id` / `prompt_version`. The registry is documented in `docs/prompt_registry.md`.

### S3.3 — Context window & memory compaction
- **Why:** Prevent unbounded growth of `hypotheses` / `citations` lists in long or complex runs and keep LLM calls under configured limits.
- **What:** `apps.agent.state.compact_history` trims hypotheses/citations based on `agent_max_hypotheses` / `agent_max_citations` in `config.py`. `_wrap_node` in `apps.agent.graph` merges node output into state, applies compaction, and feeds the compacted delta downstream. `tests/test_context_compaction.py` ensures compaction respects config and doesn’t mutate state in place.

### S3.4 — MCP/HTTP retry & circuit breaker layer
- **Why:** Make calls to MCP servers and OPA resilient to transient failures and prevent hammering unhealthy backends.
- **What:** `apps/common/http_resilience.py` implements `with_retry_sync` / `with_retry_async` with exponential backoff + jitter and a per-key circuit breaker. OPA client and MCP helper calls (Telemetry, KB, Ticketing, GitOps) now go through this layer; when circuits open, agent behaviour remains fail-closed (e.g. `opa_allow` returning False). Chaos tests exercise these paths.

### S3.5 — Chaos / degradation test harness
- **Why:** Validate behaviour under degraded conditions (slow/unavailable MCP, OPA outages) and prove the agent escalates instead of hanging or acting unsafely.
- **What:** `tests/test_chaos_degradation.py` introduces scenarios for Telemetry MCP timeouts/5xx, KB MCP unavailable, and OPA timeouts/unavailability. Investigate is expected to produce fallback hypotheses instead of raising, and Act is expected to escalate with `policy_deny` and no approvals/execution in OPA-failure cases. `docs/chaos_degradation_tests.md` explains how to run and interpret these tests.

### S3.6 — Automated dependency updates (Dependabot/Renovate)
- **Why:** Keep dependencies reasonably fresh and secure without manual chasing, while letting CI/evals enforce behavioural stability.
- **What:** `.github/dependabot.yml` configures weekly updates for pip (`requirements.txt`) and GitHub Actions with `dependencies` labels. The existing `CI` workflow already runs ruff, mypy, pytest, and evals on every PR, so Dependabot PRs are naturally gated by tests and evals. `docs/dependency_updates.md` documents the review policy (“do not merge if evals are red, even if unit tests pass”).

### S3.7 — Secrets management plan & integration path
- **Why:** Reduce long-term reliance on `.env` as the only mechanism for secrets and prepare for a Vault/cloud-secret-backed deployment.
- **What:** `apps/common/secrets.py` defines a small `SecretBackend` abstraction and an `EnvSecretBackend` default. `config.py` now sources high-value secrets via `get_secret("OPENAI_API_KEY" / "POSTGRES_PASSWORD" / "GITHUB_TOKEN" / "APPROVAL_API_KEY")`, so a future Vault/cloud backend can be wired via `set_backend(...)` without touching call sites. `docs/secrets.md` inventories current secrets and outlines a migration path from local `.env` to staging/production with a real backend and rotation strategy.

### S3.8 — Tech-debt budget process & documentation
- **Why:** Ensure that refactors, resilience work, and infra/security debt get regular capacity rather than being perpetually deferred.
- **What:** `docs/process.md` defines what counts as tech-debt work (examples/non-examples), codifies a **~20%** sprint tech-debt budget, and describes how to label/track such tasks. Sprint 3 `BOARD.md` includes a note listing S3.4–S3.8 as tech-debt examples. This lets future sprints reference a clear, lightweight process for including and reviewing debt items.

---

## 4. Project state after Sprint 3

### Observability and safety
- LLM calls and prompts are now observable via a lightweight spine, with IDs/versions that can be correlated to traces and evals.
- Context compaction ensures runs remain within configured limits while preserving key evidence.
- The injection suite remains green with unsafe-action rate = 0, and evals are wired into CI and dependency PRs.

### Resilience
- MCP/OPA interactions are more robust thanks to retries and circuit breaking; chaos tests validate behaviour under degraded backends.
- Automated dependency updates plus eval gating reduce the risk of silent regressions from library bumps.

### Process and readiness
- A secrets abstraction and plan, plus a tech-debt budget process, give a clear path from the current lab setup to a more production-like posture.
- Sprint 3’s tasks (especially S3.4–S3.8) serve as concrete examples of tech-debt work guided by that process.

---

## 5. Definition of done (sprint) — checklist

- [x] LLM observability spine records runs and calls with prompt/model metadata and integrates with OTel spans.
- [x] Prompt registry centralises and versions prompts used by the agent.
- [x] Context compaction is applied after each node and covered by tests.
- [x] HTTP/MCP retry and circuit breaker wrap OPA and MCP calls without breaking fail-closed semantics.
- [x] Chaos/degradation tests demonstrate correct escalation/fail-closed behaviour under MCP/OPA failures.
- [x] Automated dependency updates are configured and gated by lint, tests, and evals.
- [x] Secrets management abstraction and migration plan are documented and wired into config for key secrets.
- [x] Tech-debt budget process is documented and visible in sprint planning artefacts.

---

*Sprint 3 review — state at sprint close. Update if scope for 01-core Sprint 3 changes (e.g. S3.1 executed in a later hardening sprint) or additional S3 work is backported.*

