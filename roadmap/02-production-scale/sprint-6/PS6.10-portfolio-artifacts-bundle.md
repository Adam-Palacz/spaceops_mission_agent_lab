# PS6.10 - Portfolio artifacts bundle

| Field | Value |
|-------|-------|
| **Task ID** | PS6.10 |
| **Status** | Done |

---

## Description

Close **portfolio-grade** documentation for external review: one-page system README, ADR index,
threat model, runbook pack, demo script. Satisfies parent roadmap
[Cross-Cutting Engineering Artifacts](../../02-production-scale.md#cross-cutting-engineering-artifacts-portfolio-grade).

---

## Requirements

- [x] **One-page README** (or `docs/portfolio/README.md`): architecture diagram ref, run locally,
      K8s path, two demo scenarios, screenshots or trace links placeholders.
- [x] **ADR log index** - link PS1-PS6 ADRs (gateway, queue, checkpoint, LLM rollout, env, secrets).
- [x] **Threat model (1 page):** prompt injection, tool abuse, data poisoning, secrets leakage -
      mitigations point to PS4/PS5 controls.
- [x] **Runbook pack index** - single table linking all `docs/runbooks/*` with audience (dev/ops/SRE).
- [x] Dependency hygiene note: pinned deps, SBOM or `pip audit` / Dependabot reference.
- [x] Demo checklist: Scenario A (report + evidence), Scenario B (escalation), both on compose **and**
      documented cloud/local-k8s path.

---

## Dependencies

- **PS6.1-PS6.9** - runbooks and ADRs exist to index.
- **PS4** - safety/eval gates referenced in threat model.
- **PS5** - LLM backend section in portfolio README.

---

## Checklist

- [x] `docs/portfolio/README.md` (or expand root README portfolio section - avoid duplication).
- [x] `docs/threat_model.md` (1-2 pages max).
- [x] `docs/adr/README.md` - ordered ADR index with status.
- [x] Review-ready checklist for external reviewer (tick box list).

---

## Test / acceptance

- [x] External reviewer (or role-play checklist) can run demo from docs only in < 30 min setup.
- [x] Every linked runbook path resolves (link check).
- [x] Threat model maps each threat to concrete control (test, OPA, eval, or runbook).

---

## Deliverables (expected)

- `docs/portfolio/README.md`
- `docs/threat_model.md`
- `docs/adr/README.md`
- `tests/test_portfolio_ps610.py`

---

## Out of scope

- Marketing site or video production.
- Full compliance framework (SOC2, etc.).
