# Terraform

Infrastructure-as-code for cloud environments. Each subfolder is a self-contained root module.

| Subfolder | Purpose |
|-----------|---------|
| **gcp/** | GKE + Artifact Registry + billing budget for stage (`make gcp-stage-up` / `gcp-stage-down`). |

ADR: [docs/adr/0009-gcp-baseline-portable-first.md](../../docs/adr/0009-gcp-baseline-portable-first.md).
