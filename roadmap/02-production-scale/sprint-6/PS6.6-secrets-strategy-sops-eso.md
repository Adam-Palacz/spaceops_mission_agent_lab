# PS6.6 — Secrets strategy (SOPS / External Secrets)

| Field | Value |
|-------|-------|
| **Task ID** | PS6.6 |
| **Status** | Todo |

---

## Description

Define how **secrets** (`OPENAI_API_KEY`, `POSTGRES_PASSWORD`, `NGC_API_KEY`, MCP tokens) enter
the cluster without plain-text Git commits. Implement a **minimal viable path** for lab/stage; document
enterprise upgrade (ESO + GSM/Vault).

---

## Requirements

- [ ] ADR: chosen approach — **SOPS** (Git-encrypted) and/or **External Secrets Operator** stub.
- [ ] Secret naming convention per env (`spaceops-dev/openai-api-key`, etc.).
- [ ] Rotation procedure documented (even if manual for lab).
- [ ] **No secrets** in Helm values committed to repo; use `existingSecret` refs.
- [ ] Align with `config.py` / PS5.1 env var names — single mapping table.
- [ ] CI: manifest lint must not print decrypted secrets; no secret files in PR diff.

---

## Dependencies

- **PS6.1** — per-env secret paths.
- **PS6.2** — chart secretRef wiring.

---

## Checklist

- [ ] `docs/adr/0006-secrets-management-k8s.md` (or extend existing secrets stub ADR).
- [ ] Example sealed/SOPS file or ESO `ExternalSecret` template (placeholder values).
- [ ] Runbook: bootstrap secrets on fresh cluster.
- [ ] `.gitignore` / pre-commit note for decrypted secret artifacts.

---

## Test / acceptance

- [ ] Local deploy succeeds with secrets supplied via documented mechanism.
- [ ] `git grep OPENAI_API_KEY` in tracked files finds only `.env.example` placeholders.
- [ ] Reviewer can rotate one secret following runbook without guessing paths.

---

## Deliverables (expected)

- `docs/adr/0006-secrets-management-k8s.md`
- `docs/runbooks/k8s_secrets_bootstrap.md`
- Example manifests under `deploy/*/examples/secrets/`

---

## Out of scope

- Full Vault HA deployment.
- Automated rotation Lambdas (Phase 7 enterprise).
