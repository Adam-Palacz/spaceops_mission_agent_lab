# PS6.6 — Kubernetes secrets examples (placeholders only)

Examples for [ADR 0007](../../../docs/adr/0007-secrets-management-k8s.md). **Never commit real credentials.**

| Path | Purpose |
|------|---------|
| [local/bootstrap-secret.yaml.example](local/bootstrap-secret.yaml.example) | Manual `kubectl apply` for dev lab |
| [sops/spaceops-dev-secrets.sops.yaml.example](sops/spaceops-dev-secrets.sops.yaml.example) | SOPS-encrypted Secret shape (encrypt before commit) |
| [eso/external-secret-stage.yaml.example](eso/external-secret-stage.yaml.example) | ESO `ExternalSecret` for stage |
| [eso/secret-store-gcp-sm.yaml.example](eso/secret-store-gcp-sm.yaml.example) | GCP Secret Manager `SecretStore` stub |

Runbook: [docs/runbooks/k8s_secrets_bootstrap.md](../../../docs/runbooks/k8s_secrets_bootstrap.md)

Bootstrap helper: `make k8s-secrets-bootstrap` or `python scripts/k8s_secrets_bootstrap.py`
