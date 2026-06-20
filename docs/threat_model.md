# Threat model — SpaceOps Mission Agent Lab (PS6.10)

One-page threat model for portfolio review. Detailed prompt-injection analysis:
[prompt_injection_threat_model.md](prompt_injection_threat_model.md) (PS4.3).

**Scope:** agent API, LangGraph runtime, MCP tool boundary, KB/telemetry ingest, secrets in K8s/cloud.
**Out of scope:** SOC2, org-wide IAM landing zone, external LLM firewall SaaS.

---

## Assets

| Asset | Sensitivity | Storage / path |
|-------|-------------|----------------|
| LLM API keys | High | `.env`, K8s Secrets / GSM (PS6.6) |
| GitHub tokens (GitOps) | High | `.env`, secrets manager |
| Telemetry / incident payloads | Medium | Postgres, `data/telemetry/` |
| KB runbooks / postmortems | Medium | pgvector, `kb/` |
| Audit / trace data | Medium | Postgres audit, Jaeger |
| Agent reports & escalation packets | Medium | API response, Postgres |

---

## Threat matrix

| # | Threat | Attack vector | Impact | Control(s) | Verification |
|---|--------|---------------|--------|------------|--------------|
| T1 | **Prompt injection** | Malicious text in incident `payload`, KB snippets, or model `plan` | Policy bypass, unsafe tool calls, data exfil instructions | Pattern scan + sanitization fences; fail-closed escalation; plan allowlist | `apps/agent/prompt_injection.py`; `tests/test_prompt_injection_ps43.py`; `evals/scoring` injection suite (MoE3 unsafe=0) |
| T2 | **Tool abuse** | Agent invokes restricted `action_type` or exceeds tool budget | Unauthorized config change, spurious tickets/PRs | MCP-only boundary (no shell); OPA Rego deny-by-default; HITL approval for restricted steps | `infra/opa/agent_policy.rego`; `tests/test_act_opa_policy.py`; [guardrails_minimum_hardening.md](runbooks/guardrails_minimum_hardening.md) |
| T3 | **Data poisoning** | Poisoned KB doc or telemetry fixture skews triage | Wrong subsystem, false confidence, bad citations | Untrusted-data fences; citation requirements; escalation on `no_evidence` / `conflicting_signals`; eval cases | `evals/cases.yaml`; semantic evals; [output_schema.md](output_schema.md) PS4.2 |
| T4 | **Secrets leakage** | Committed `.env`, plaintext Helm values, logs printing keys | Credential theft, supply-chain compromise | `.gitignore`; `secrets.create: false` stage/prod; ESO/SOPS ADR 0007; no secrets in GitOps manifests | `tests/test_helm_ps66.py`; [k8s_secrets_bootstrap.md](runbooks/k8s_secrets_bootstrap.md); pre-commit / CI secret patterns |
| T5 | **LLM cost abuse** | Runaway loops, high token volume | Unexpected API spend (model $) | Per-run call limits; daily token budget (`LLM_DAILY_TOKEN_BUDGET`); escalation on exceed | [llm_cost_guardrails.md](llm_cost_guardrails.md); `tests/test_llm_cost_guardrails_ps56.py` |
| T6 | **Infra cost abuse** | Orphan GKE/LB/disk left running | Unexpected cloud spend (infra $) | PS6.9 budgets, scale-down scripts, labels; no GPU pool by default | [cloud_cost_hygiene.md](runbooks/cloud_cost_hygiene.md); `infra/terraform/gcp/budget.tf` |
| T7 | **Denial of service** | Large payloads, slow MCP, LLM timeouts | Failed runs, operator fatigue | Timeouts (`AGENT_*_TIMEOUT`); tool failure → escalation; rate limits at gateway (process budget) | `tests/test_guardrails_ps17.py`; [ci_gating_policy.md](runbooks/ci_gating_policy.md) |
| T8 | **Supply chain** | Vulnerable dependencies | RCE, credential access | Pinned `requirements.txt`; Dependabot; `pip audit` (manual) | [.github/dependabot.yml](../.github/dependabot.yml); [portfolio README](portfolio/README.md) |

---

## Trust boundaries

```
Untrusted                    Trust boundary              Trusted
─────────                    ──────────────              ───────
Operator/API payload  ──►  Prompt injection guard  ──►  LLM prompt (sanitized)
KB / telemetry text   ──►  Citation + escalation   ──►  Investigation context
Model plan steps      ──►  OPA + allowlist         ──►  MCP tool calls
Restricted actions    ──►  Approval API + OPA      ──►  GitOps / config change
```

Agent **never** executes arbitrary shell. All side effects go through named MCP tools with explicit
schemas and audit records (`roadmap/goals.md` §4.3).

---

## PS4 / PS5 control mapping

| PS area | Controls referenced in this model |
|---------|-----------------------------------|
| **PS4.2** | Output schema validation — `output_schema_violation` escalation |
| **PS4.3** | Prompt injection guards — T1 |
| **PS4.4** | Semantic evals, audit semantics |
| **PS4.6** | Behavior metrics (escalation rate, evidence coverage) |
| **PS4.7** | CI hard gates — OPA, injection, golden baselines |
| **PS4.8** | Shadow models / promotion evidence |
| **PS5.4** | LLM backend fallback (availability, not authorization) |
| **PS5.6** | Token budget — T5 |
| **PS5.7** | GPU idle TTL (local compose only) |
| **PS6.5** | K8s NetworkPolicy / RBAC — lateral movement reduction |
| **PS6.6** | Secrets — T4 |
| **PS6.9** | Cloud cost — T6 |

---

## Residual risks (accepted for lab / portfolio)

- No external LLM firewall (Lakera etc.) — pattern guards only.
- KB quarantine is manual — operators review audit + re-index.
- `LLM_BUDGET_MODE=postgres` org-wide cap on stage/prod (PS7.6); dev stays `process` (ADR 0005).
- Local `.env` file is operator responsibility on laptops.
- TLS deferred on lab GKE LoadBalancer (PS6.8).

---

## Incident response pointers

| Symptom | Runbook |
|---------|---------|
| Injection suspected in production payload | [guardrails_quality_triage.md](runbooks/guardrails_quality_triage.md) |
| OPA deny spike | [ci_gating_policy.md](runbooks/ci_gating_policy.md) |
| Token budget exceeded | [llm_cost_guardrails.md](runbooks/llm_cost_guardrails.md) |
| GCP bill alert | [cloud_cost_hygiene.md](runbooks/cloud_cost_hygiene.md) |
| Trace/debug a run | [distributed_tracing_ps19.md](runbooks/distributed_tracing_ps19.md), [replay_workflow.md](runbooks/replay_workflow.md) |

---

## References

- [Portfolio README](portfolio/README.md)
- [ADR index](adr/README.md)
- [prompt_injection_threat_model.md](prompt_injection_threat_model.md)
