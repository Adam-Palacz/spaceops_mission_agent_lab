# Secrets management plan (S3.7)

This document describes how secrets are handled today (local `.env`) and the path toward
using a dedicated secrets backend (Vault / cloud secret manager) in staging/production.

## 1. Inventory of secrets

Logical secrets currently used by the system (from `config.py` / `.env.example`):

- `OPENAI_API_KEY` — OpenAI API key for evals and the agent.
- `POSTGRES_PASSWORD` / `DATABASE_URL` — DB credentials for KB/RAG.
- `GITHUB_TOKEN` — token with `repo` scope for GitOps PRs.
- `APPROVAL_API_KEY` — key for `/approvals` API (authN for approve/reject).
- Optional observability / infra secrets (depending on deployment):
  - `OTEL_EXPORTER_OTLP_ENDPOINT` (collector with auth),
  - any future MCP tokens or cloud credentials.

Most other values in `config.py` are **non‑secret config** (URLs, timeouts, feature flags).

## 2. Target secrets backend (non-local)

For non-local environments (staging/prod), the plan is to use a managed secrets backend,
such as **HashiCorp Vault** or a cloud secrets manager (AWS/GCP/Azure). The choice is
deployment-specific, but the agent code only depends on a small abstraction:

```python
from apps.common.secrets import get_secret

api_key = get_secret("OPENAI_API_KEY", "")
```

Today `get_secret()` reads from environment variables; in the future, the backend can be
swapped to call Vault / cloud APIs without changing call sites.

## 3. Abstraction layer in code

File: `apps/common/secrets.py`

- `SecretBackend` protocol: `.get(name) -> str | None`.
- `EnvSecretBackend`: default backend that reads from `os.environ` (and therefore from
  `.env` in local dev).
- `set_backend(backend)`: hook for tests or for wiring a real backend at process start.
- `get_secret(name, default)`: main entry point used by code.

`config.py` uses this stub for high-value secrets:

- `openai_api_key` ← `get_secret("OPENAI_API_KEY", "")`
- `postgres_password` ← `get_secret("POSTGRES_PASSWORD", "")`
- `github_token` ← `get_secret("GITHUB_TOKEN", "")`
- `approval_api_key` ← `get_secret("APPROVAL_API_KEY", "")`

Pydantic `BaseSettings` still supports overriding via env vars; `.env` remains convenient
for local work, but the **logical source of truth is `get_secret()`**.

## 4. Migration path

1. **Local dev (today)**  
   - Keep using `.env` (not committed) with the same variables as before.
   - `EnvSecretBackend` reads from `os.environ`, so behaviour is unchanged.

2. **Staging**  
   - Provision a secrets backend (e.g. Vault) and store:
     - `OPENAI_API_KEY`,
     - `POSTGRES_PASSWORD` (or `DATABASE_URL`),
     - `GITHUB_TOKEN` (if GitOps is enabled),
     - `APPROVAL_API_KEY`.
   - Implement a `VaultSecretBackend` (or cloud-specific backend) that implements
     `SecretBackend` and reads from the chosen service.
   - At process startup (e.g. in `apps/api/main.py` / entrypoint script), call
     `set_backend(VaultSecretBackend(...))` **before** importing `config`.

3. **Production**  
   - Remove `.env` from production hosts; only the backend provides secrets.
   - Rotate secrets using the backend’s native features (time-limited tokens, rotation
     policies); `get_secret()` remains unchanged.

4. **Rotation policy**  
   - OPENAI / cloud API keys: rotate regularly (e.g. monthly or on incident).
   - DB passwords: rotate with coordinated rollout (update backend, then restart services).
   - Approval API keys: rotate and invalidate old keys after a short overlap window.

## 5. Kubernetes (PS6.6)

For Helm / kind deployments, secrets use the same **env var names** as Compose. See
[ADR 0007](adr/0007-secrets-management-k8s.md) and [runbooks/k8s_secrets_bootstrap.md](runbooks/k8s_secrets_bootstrap.md).

| App env (`config.py`) | K8s Secret `data` key | ESO / GSM path (`{env}` = dev\|stage\|prod) |
|-----------------------|----------------------|---------------------------------------------|
| `POSTGRES_PASSWORD` | `postgres-password` | `spaceops-{env}/postgres-password` |
| `OPENAI_API_KEY` | `OPENAI_API_KEY` | `spaceops-{env}/openai-api-key` |
| `APPROVAL_API_KEY` | `APPROVAL_API_KEY` | `spaceops-{env}/approval-api-key` |
| `GITHUB_TOKEN` | `GITHUB_TOKEN` | `spaceops-{env}/github-token` |
| `NGC_API_KEY` | `NGC_API_KEY` | `spaceops-{env}/ngc-api-key` |
| `CURSOR_SH_API_KEY` | `CURSOR_SH_API_KEY` | `spaceops-{env}/cursor-sh-api-key` |
| `GPU_LLM_API_KEY` | `GPU_LLM_API_KEY` | `spaceops-{env}/gpu-llm-api-key` |

Examples: `deploy/examples/secrets/`. Bootstrap: `make k8s-secrets-bootstrap`.

---

## 6. First secret to migrate

Priority secret to move under the new mechanism: **`OPENAI_API_KEY`**.

Reasoning:

- It gates all LLM calls (agent + evals),
- It is highly sensitive,
- It has a clear, single use in `config.py` and evals.

Once `OPENAI_API_KEY` is coming from the secrets backend in staging, the same pattern
can be applied to `POSTGRES_PASSWORD`, `GITHUB_TOKEN`, and `APPROVAL_API_KEY`.

