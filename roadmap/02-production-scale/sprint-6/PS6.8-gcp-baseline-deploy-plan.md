# PS6.8 - GCP baseline deploy plan (portable-first)

| Field | Value |
|-------|-------|
| **Task ID** | PS6.8 |
| **Status** | Done |

---

## Description

Minimal **GCP-first** cloud path that keeps app manifests **portable** (Phase 7): Terraform skeleton,
Artifact Registry design, optional small GKE cluster. Not a full production landing zone.

**Done levels (see sprint README DoD):**

- **Minimum (no live GCP):** ADR + `infra/terraform/gcp/` skeleton; `terraform validate`; README for vars/state; portability narrative.
- **Stretch:** reproducible deploy to stage GKE using PS6.2 Helm + values overlays.

---

## Requirements

- [x] Terraform (or documented equivalent) for: project vars, GKE cluster (small), Artifact Registry,
      service accounts for deploy.
- [x] **(Stretch)** Deploy PS6.2 chart to GKE using same values overlays as local (portability proof).
- [x] **No cloud lock-in in app layer** - no GKE-only APIs in application code.
- [x] Document optional Cloud Run path as **fallback/showcase** (parent Phase 7 note).
- [x] Ingress: minimal (LoadBalancer or Ingress) for API; document TLS deferral for lab.
- [x] CI: optional workflow to build/push images to Artifact Registry (`workflow_dispatch`).

---

## Dependencies

- **PS6.1** - stage/prod env definitions.
- **PS6.2** - Helm package.
- **PS6.6** - secrets in cloud (GSM + ESO design note minimum).

---

## Checklist

- [x] `infra/terraform/gcp/` with README (vars, state backend note).
- [x] `docs/runbooks/gcp_stage_deploy.md`
- [x] Cost estimate section (cluster size, always-on vs stop).
- [x] Cross-link PS6.9 billing controls.

---

## Test / acceptance

- [x] **Minimum:** `terraform validate` passes in CI or a documented local gate.
- [x] **Minimum:** README documents vars, state backend posture, cost estimate, and deploy/destroy flow.
- [ ] **Stretch:** one engineer can destroy and recreate stage cluster from docs (time-boxed).
- [ ] **Stretch:** demo scenario A/B runs in cloud with traces (replay optional).

---

## Deliverables (expected)

- `infra/terraform/gcp/`
- `docs/runbooks/gcp_stage_deploy.md`
- `docs/adr/0009-gcp-baseline-portable-first.md`
- `deploy/helm/spaceops/values-gcp-stage.yaml`
- `.github/workflows/gcp-terraform-validate.yml`
- `.github/workflows/gcp-artifact-registry-push.yml`

---

## Out of scope

- Multi-region HA.
- GPU node pool (Phase 7 PS7.x).
