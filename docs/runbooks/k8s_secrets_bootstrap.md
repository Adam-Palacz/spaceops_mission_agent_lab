# PS6.6 — Bootstrap and rotate Kubernetes secrets for SpaceOps

How secrets enter the cluster per [ADR 0007](../adr/0007-secrets-management-k8s.md). For the
application-level abstraction see [secrets.md](../secrets.md).

## Secret naming (quick reference)

| Environment | Namespace | K8s Secret | Example store path (ESO/GSM) |
|-------------|-----------|------------|--------------------------------|
| dev | `spaceops-dev` | `spaceops-dev-secrets` | `spaceops-dev/postgres-password` |
| stage | `spaceops-stage` | `spaceops-stage-secrets` | `spaceops-stage/openai-api-key` |
| prod | `spaceops-prod` | `spaceops-prod-secrets` | `spaceops-prod/openai-api-key` |

### Env var → Secret key mapping

| App env (`config.py`) | K8s Secret `data` key |
|-----------------------|----------------------|
| `POSTGRES_PASSWORD` | `postgres-password` |
| `OPENAI_API_KEY` | `OPENAI_API_KEY` |
| `APPROVAL_API_KEY` | `APPROVAL_API_KEY` |
| `GITHUB_TOKEN` | `GITHUB_TOKEN` |
| `NGC_API_KEY` | `NGC_API_KEY` |
| `CURSOR_SH_API_KEY` | `CURSOR_SH_API_KEY` |
| `GPU_LLM_API_KEY` | `GPU_LLM_API_KEY` |

Helm workloads mount these via `secretKeyRef` (see `deploy/helm/spaceops/templates/`).

---

## Dev lab — path A: Helm renders Secret (default `make k8s-up`)

`values-dev.yaml` sets `secrets.create: true`. Password comes from install-time `--set` only:

```powershell
$env:K8S_POSTGRES_PASSWORD = "spaceops"
make k8s-up
```

`scripts/k8s_local.py` passes `--set secrets.postgresPassword=$K8S_POSTGRES_PASSWORD`.

Optional OpenAI key at install:

```powershell
helm upgrade --install spaceops deploy/helm/spaceops `
  -f deploy/helm/spaceops/values.yaml `
  -f deploy/helm/spaceops/values-dev.yaml `
  -f deploy/helm/spaceops/values-minimal-dev.yaml `
  --namespace spaceops-dev --create-namespace `
  --set secrets.postgresPassword=$env:K8S_POSTGRES_PASSWORD `
  --set secrets.openaiApiKey=$env:OPENAI_API_KEY
```

**Never commit** non-empty `secrets.postgresPassword` or API keys in values YAML.

---

## Dev lab — path B: pre-create Secret (`secrets.create=false`)

1. Export values from `.env` (same names as Compose):

   ```powershell
   $env:K8S_POSTGRES_PASSWORD = "spaceops"
   $env:OPENAI_API_KEY = "<from .env>"
   ```

2. Bootstrap:

   ```powershell
   make k8s-secrets-bootstrap
   # or: python scripts/k8s_secrets_bootstrap.py --create-namespace
   ```

3. Install Helm with `secrets.create=false` and matching `existingSecret`:

   ```powershell
   helm upgrade --install spaceops deploy/helm/spaceops `
     ... `
     --set secrets.create=false `
     --set secrets.existingSecret=spaceops-dev-secrets `
     --set postgres.auth.existingSecret=spaceops-dev-secrets
   ```

Example manifest: `deploy/examples/secrets/local/bootstrap-secret.yaml.example`

---

## Stage / prod — External Secrets Operator (recommended)

1. Install [External Secrets Operator](https://external-secrets.io/) on the cluster.
2. Create secrets in GSM/Vault using paths from ADR 0007 (`spaceops-stage/openai-api-key`, …).
3. Apply `SecretStore` — example: `deploy/examples/secrets/eso/secret-store-gcp-sm.yaml.example`
4. Apply `ExternalSecret` — example: `deploy/examples/secrets/eso/external-secret-stage.yaml.example`
   or enable chart stub: `externalSecrets.enabled=true` in values overlay.
5. Verify:

   ```bash
   kubectl get externalsecret,secret -n spaceops-stage
   helm upgrade --install spaceops deploy/helm/spaceops \
     -f deploy/helm/spaceops/values.yaml \
     -f deploy/helm/spaceops/values-stage.yaml \
     --namespace spaceops-stage --create-namespace
   ```

Stage/prod overlays set `secrets.create: false` and `secrets.existingSecret`.

---

## SOPS (Git-encrypted alternative)

For GitOps repos that store encrypted secrets in Git:

1. Copy `deploy/examples/secrets/sops/spaceops-dev-secrets.sops.yaml.example`.
2. Replace `REPLACE_*` placeholders locally.
3. Encrypt with SOPS (age or PGP); store encrypted file outside this repo or in a private branch.
4. Decrypt at deploy time only: `sops -d file.sops.yaml | kubectl apply -f -`

**Do not commit** decrypted `*.dec.yaml` files (listed in `.gitignore`).

---

## Rotation (manual lab procedure)

Example: rotate `OPENAI_API_KEY` in **dev**.

1. Update the source:
   - Path A: `helm upgrade ... --set secrets.openaiApiKey=$NEW_KEY --reuse-values`
   - Path B / ESO: update backend or re-run bootstrap with new env var.
2. Restart API to pick up Secret:

   ```bash
   kubectl rollout restart deployment/spaceops-api -n spaceops-dev
   kubectl rollout status deployment/spaceops-api -n spaceops-dev
   ```

3. Smoke: `make k8s-smoke` or `curl` via port-forward `/health`.
4. Optional LLM check: trigger one agent run or `POST /runs` with test payload.

For **Postgres password**, also update the database user password inside Postgres before
restarting StatefulSet, or use a coordinated maintenance window.

---

## CI / pre-commit hygiene

- CI `helm template` uses placeholder `--set secrets.postgresPassword=ci-dev-only` for dev only.
- Stage/prod template jobs must not emit `stringData` Secrets.
- Do not pipe `helm template` output containing real keys to logs.
- Decrypted SOPS artifacts belong in `.gitignore` (`deploy/secrets/decrypted/`, `*.dec.yaml`).

Verify no real key material in tracked files (env **names** in docs/tests/templates are OK):

```bash
git grep -E 'sk-[a-zA-Z0-9]{20,}|nvapi-|ghp_' -- ':!.env' ':!deploy/examples/secrets/'
# Expect: no matches
```

---

## Related

- [local_k8s_dev.md](local_k8s_dev.md) — kind bootstrap
- [environment_promotion.md](environment_promotion.md) — dev → stage → prod
- [deploy/examples/secrets/README.md](../../deploy/examples/secrets/README.md)
