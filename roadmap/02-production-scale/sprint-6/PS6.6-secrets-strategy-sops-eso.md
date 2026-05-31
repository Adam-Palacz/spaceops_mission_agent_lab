# PS6.6 — Secrets strategy (SOPS / External Secrets)

| Field | Value |
|-------|-------|
| **Task ID** | PS6.6 |
| **Status** | Done |

---

## Description

Define how **secrets** (`OPENAI_API_KEY`, `POSTGRES_PASSWORD`, `NGC_API_KEY`, MCP tokens) enter
the cluster without plain-text Git commits. Implement a **minimal viable path** for lab/stage; document
enterprise upgrade (ESO + GSM/Vault).

---

## Requirements

- [x] ADR: chosen approach — **SOPS** (Git-encrypted) and/or **External Secrets Operator** stub.
- [x] Secret naming convention per env (`spaceops-dev/openai-api-key`, etc.).
- [x] Rotation procedure documented (even if manual for lab).
- [x] **No secrets** in Helm values committed to repo; use `existingSecret` refs.
- [x] Align with `config.py` / PS5.1 env var names — single mapping table.
- [x] CI: manifest lint must not print decrypted secrets; no secret files in PR diff.

---

## Dependencies

- **PS6.1** — per-env secret paths.
- **PS6.2** — chart secretRef wiring.

---

## Checklist

- [x] `docs/adr/0007-secrets-management-k8s.md` (0006 reserved for Helm packaging ADR).
- [x] Example sealed/SOPS file or ESO `ExternalSecret` template (placeholder values).
- [x] Runbook: bootstrap secrets on fresh cluster.
- [x] `.gitignore` / pre-commit note for decrypted secret artifacts.

---

## Test / acceptance

- [x] Local deploy succeeds with secrets supplied via documented mechanism.
- [x] Secret-pattern scan finds no committed real key values; env names may appear in docs, tests, templates, and placeholder examples.
- [x] Reviewer can rotate one secret following runbook without guessing paths.

---

## Deliverables (expected)

- `docs/adr/0007-secrets-management-k8s.md`
- `docs/runbooks/k8s_secrets_bootstrap.md`
- Example manifests under `deploy/examples/secrets/`

---

## Out of scope

- Full Vault HA deployment.
- Automated rotation Lambdas (Phase 7 enterprise).
