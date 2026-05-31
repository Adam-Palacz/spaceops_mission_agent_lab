# ADR 0007 — Kubernetes secrets management (SOPS / External Secrets)

- **Status:** Accepted
- **Date:** 2026-05-29
- **Related:** PS6.6, [ADR 0005](0005-environment-strategy-dev-stage-prod.md), [ADR 0006](0006-kubernetes-packaging-helm.md), [docs/secrets.md](../secrets.md)

## Context

SpaceOps uses sensitive values (`OPENAI_API_KEY`, `POSTGRES_PASSWORD`, `NGC_API_KEY`, GitHub and
approval keys) in Compose via local `.env` and in Kubernetes via Helm `secretKeyRef`. PS6.2 wired
`secrets.create` for dev lab installs; stage/prod overlays must not commit plaintext credentials.

We need one documented path for:

- how secrets enter a cluster per environment,
- naming and rotation,
- alignment with `config.py` / `get_secret()` env var names,
- and CI safety (no decrypted material in Git or PR logs).

## Decision

### 1. Layered approach (lab → enterprise)

| Tier | Environment | Mechanism | Git contents |
|------|-------------|-----------|--------------|
| **Lab** | `dev` (local kind) | Helm `secrets.create=false` **or** `true` with values supplied only via `--set` / env at install time; optional `make k8s-secrets-bootstrap` | Example SOPS files with placeholders only |
| **Integration** | `stage` | **External Secrets Operator (ESO)** stub + GSM/Vault `SecretStore` (operator installed out-of-band) | `ExternalSecret` templates with store key refs, no values |
| **Enterprise** | `prod` | Same as stage; mandatory ESO + managed backend; SOPS optional for GitOps repos | Encrypted manifests or ESO-only |

**SOPS** (Mozilla SOPS + age/PGP) is the **Git-encrypted** option for teams that want secrets in
Git without plaintext. **ESO** is the **runtime sync** option for stage/prod clusters.

Both use the **same Kubernetes Secret name and data keys** so Helm does not change between tiers.

### 2. Kubernetes Secret naming

| Environment | Namespace | Secret name (`secrets.existingSecret`) |
|-------------|-----------|----------------------------------------|
| dev | `spaceops-dev` | `spaceops-dev-secrets` (default when not using `secrets.create`) |
| stage | `spaceops-stage` | `spaceops-stage-secrets` |
| prod | `spaceops-prod` | `spaceops-prod-secrets` |

Helm release name remains `spaceops`; secret name is **env-scoped**, not release-scoped.

### 3. Backend store paths (ESO / Vault / GSM)

Logical paths (ESO `remoteRef.key` or Vault path segment):

| Store path | K8s Secret `data` key | App env (`config.py`) |
|------------|----------------------|------------------------|
| `spaceops-{env}/postgres-password` | `postgres-password` | `POSTGRES_PASSWORD` |
| `spaceops-{env}/openai-api-key` | `OPENAI_API_KEY` | `OPENAI_API_KEY` |
| `spaceops-{env}/approval-api-key` | `APPROVAL_API_KEY` | `APPROVAL_API_KEY` |
| `spaceops-{env}/github-token` | `GITHUB_TOKEN` | `GITHUB_TOKEN` |
| `spaceops-{env}/ngc-api-key` | `NGC_API_KEY` | `NGC_API_KEY` |
| `spaceops-{env}/cursor-sh-api-key` | `CURSOR_SH_API_KEY` | `CURSOR_SH_API_KEY` |
| `spaceops-{env}/gpu-llm-api-key` | `GPU_LLM_API_KEY` | `GPU_LLM_API_KEY` |

`{env}` is `dev`, `stage`, or `prod`. MCP-specific tokens follow the same pattern when added
(`spaceops-{env}/mcp-<name>-token`).

### 4. Helm contract (PS6.6)

- **`secrets.create: true`** — render a `Secret` only in lab; **never** commit non-empty
  `secrets.postgresPassword` / `secrets.openaiApiKey` in values files.
- **`secrets.create: false`** — chart references `secrets.existingSecret` (and
  `postgres.auth.existingSecret` must match).
- Workloads use `secretKeyRef` with `optional: true` for keys not required in minimal profile.
- Optional chart values `externalSecrets.enabled` render an `ExternalSecret` stub (off by default).

### 5. Rotation (lab manual procedure)

1. Update value in backend (GSM/Vault) or re-encrypt SOPS file.
2. For ESO: wait for sync or `kubectl annotate externalsecret ... force-sync=1`.
3. For static Secret: `kubectl delete secret <name> -n <ns>` then re-apply / re-run bootstrap.
4. Rolling restart affected Deployments (`kubectl rollout restart deployment/...`).
5. Verify: API `/health`, one guarded LLM call, Postgres connectivity.

Documented in [docs/runbooks/k8s_secrets_bootstrap.md](../runbooks/k8s_secrets_bootstrap.md).

### 6. CI and pre-commit

- `helm template` in CI uses **placeholder** `--set secrets.postgresPassword=ci-dev-only` only for
  dev render jobs; stage/prod templates must not emit `stringData` Secrets.
- Manifest lint must not pipe decrypted secrets to logs.
- Decrypted SOPS artifacts (`*.dec.yaml`, `deploy/secrets/decrypted/`) are **gitignored**.
- Reviewers run secret-pattern scans; literal env names such as `OPENAI_API_KEY` may appear in
  docs, tests, templates, and placeholder examples, but no real key values may be committed.

## Consequences

- **Positive:** Single mapping table; stage/prod ready for ESO; dev stays simple with `--set` or bootstrap script.
- **Negative:** Operators must install ESO + backend for stage/prod (out of scope for PS6.6 full HA).
- **Follow-up:** PS6.7 GitOps may consume SOPS-encrypted manifests; Phase 7 Vault HA.

## References

- Examples: `deploy/examples/secrets/`
- Runbook: `docs/runbooks/k8s_secrets_bootstrap.md`
- Code stub: `apps/common/secrets.py` (unchanged interface)
