# ADR 0006 — Kubernetes packaging with Helm

- **Status:** Accepted
- **Date:** 2026-05-29
- **Related:** PS6.2, [ADR 0005](0005-environment-strategy-dev-stage-prod.md)

## Context

PS6 packages SpaceOps for platform operations. We need portable Kubernetes manifests with
environment overlays (`dev` / `stage` / `prod`) and a minimal safe baseline (api, postgres, opa,
telemetry-mcp, telemetry-persister).

Alternatives considered: **kustomize** (flat overlays) vs **Helm** (values + templates).

## Decision

1. Use **Helm** under `deploy/helm/spaceops/`.
2. Do **not** maintain Helm and kustomize in parallel.
3. Layer values: `values.yaml` → `values-{dev,stage,prod}.yaml` → optional `values-minimal-dev.yaml`.
4. **Minimal dev profile** ships first; optional toggles for MCPs, observability, NIM/GPU.
5. **CI gate:** `helm template` for all env overlays (`.github/workflows/k8s-manifest-lint.yml`).
6. **Secrets:** dev may use `secrets.create` + `--set`; stage/prod use external secret refs (PS6.6).
7. **Agent worker:** Variant B (api checkpoint) default; `agentWorker.enabled` stub for Variant A defer.

## Consequences

- PS6.3 (`make k8s-up`) installs this chart on kind/k3d.
- PS6.8 GKE deploy reuses the same values overlays (portability).
- OPA policy bundled in chart `policy/` (sync from `infra/opa/` when policy changes).

## References

- [Chart README](../../deploy/helm/spaceops/README.md)
- [Environment strategy ADR](0005-environment-strategy-dev-stage-prod.md)
