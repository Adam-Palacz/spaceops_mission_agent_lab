# PR2.3 - Security review: OPA, approvals, MCP, audit

## Description

Perform a focused security review of the control boundaries that make SpaceOps safe: no shell
access, MCP-only tools, OPA fail-closed policy, authenticated approvals, append-only audit, LLM
budget enforcement, and platform ops gating.

## Requirements

- Review OPA fail-closed behavior under down, timeout, malformed policy response, and deny.
- Review approval authn/authz, idempotency, and audit attribution.
- Review MCP tool allowlist and argument validation.
- Review append-only audit behavior and tamper-evidence limitations.
- Review platform ops triage `--apply` gating.
- Review LLM gateway budget/circuit breaker/fallback controls.

## Checklist

- [ ] Security review checklist added.
- [ ] Findings recorded with severity and owner.
- [ ] At least one negative test/drill per boundary.
- [ ] Critical/high issues fixed or explicitly block phase closure.
- [ ] Accepted risks recorded in phase review.

## Test requirements

- Focused tests for security boundary regressions.
- Documentation evidence for accepted risks.

