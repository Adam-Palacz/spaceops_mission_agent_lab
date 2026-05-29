# PS6.10 — Portfolio artifacts bundle

| Field | Value |
|-------|-------|
| **Task ID** | PS6.10 |
| **Status** | Todo |

---

## Description

Close **portfolio-grade** documentation for external review: one-page system README, ADR index,
threat model, runbook pack, demo script. Satisfies parent roadmap [Cross-Cutting Engineering Artifacts](../../02-production-scale.md#cross-cutting-engineering-artifacts-portfolio-grade).

---

## Requirements

- [ ] **One-page README** (or `docs/portfolio/README.md`): architecture diagram ref, run locally,
      K8s path, two demo scenarios, screenshots or trace links placeholders.
- [ ] **ADR log index** — link PS1–PS6 ADRs (gateway, queue, checkpoint, LLM rollout, env, secrets…).
- [ ] **Threat model (1 page):** prompt injection, tool abuse, data poisoning, secrets leakage —
      mitigations point to PS4/PS5 controls.
- [ ] **Runbook pack index** — single table linking all `docs/runbooks/*` with audience (dev/ops/SRE).
- [ ] Dependency hygiene note: pinned deps, SBOM or `pip audit` / Dependabot reference.
- [ ] Demo checklist: Scenario A (report + evidence), Scenario B (escalation), both on compose **and**
      documented cloud/local-k8s path.

---

## Dependencies

- **PS6.1–PS6.9** — runbooks and ADRs exist to index.
- **PS4** — safety/eval gates referenced in threat model.
- **PS5** — LLM backend section in portfolio README.

---

## Checklist

- [ ] `docs/portfolio/README.md` (or expand root README portfolio section — avoid duplication).
- [ ] `docs/threat_model.md` (1–2 pages max).
- [ ] `docs/adr/README.md` — ordered ADR index with status.
- [ ] Review-ready checklist for external reviewer (tick box list).

---

## Test / acceptance

- [ ] External reviewer (or role-play checklist) can run demo from docs only in &lt; 30 min setup.
- [ ] Every linked runbook path resolves (link check).
- [ ] Threat model maps each threat to concrete control (test, OPA, eval, or runbook).

---

## Deliverables (expected)

- `docs/portfolio/README.md`
- `docs/threat_model.md`
- `docs/adr/README.md`

---

## Out of scope

- Marketing site or video production.
- Full compliance framework (SOC2, etc.).
