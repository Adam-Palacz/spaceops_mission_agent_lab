# PS6.8 — GCP baseline deploy plan (portable-first)

| Field | Value |
|-------|-------|
| **Task ID** | PS6.8 |
| **Status** | Todo |

---

## Description

Minimal **GCP-first** cloud path that keeps app manifests **portable** (Phase 7): Terraform skeleton,
Artifact Registry design, optional small GKE cluster. Not a full production landing zone.

**Done levels (see sprint README DoD):**

- **Minimum (no live GCP):** ADR + `infra/terraform/gcp/` skeleton; `terraform validate`; README for vars/state; portability narrative.
- **Stretch:** reproducible deploy to stage GKE using PS6.2 Helm + values overlays.

---

## Requirements

- [ ] Terraform (or documented equivalent) for: project vars, GKE cluster (small), Artifact Registry,
      service accounts for deploy.
- [ ] **(Stretch)** Deploy PS6.2 chart to GKE using same values overlays as local (portability proof).
- [ ] **No cloud lock-in in app layer** — no GKE-only APIs in application code.
- [ ] Document optional Cloud Run path as **fallback/showcase** (parent Phase 7 note).
- [ ] Ingress: minimal (LoadBalancer or Ingress) for API; document TLS deferral for lab.
- [ ] CI: optional workflow to build/push images to Artifact Registry (workflow_dispatch).

---

## Dependencies

- **PS6.1** — stage/prod env definitions.
- **PS6.2** — Helm package.
- **PS6.6** — secrets in cloud (GSM + ESO design note minimum).

---

## Checklist

- [ ] `infra/terraform/gcp/` with README (vars, state backend note).
- [ ] `docs/runbooks/gcp_stage_deploy.md`
- [ ] Cost estimate section (cluster size, always-on vs stop).
- [ ] Cross-link PS6.9 billing controls.

---

## Test / acceptance

- [ ] **Minimum:** `terraform validate` passes in CI or a documented local gate.
- [ ] **Minimum:** README documents vars, state backend posture, cost estimate, and deploy/destroy flow.
- [ ] **Stretch:** one engineer can destroy and recreate stage cluster from docs (time-boxed).
- [ ] **Stretch:** demo scenario A/B runs in cloud with traces (replay optional).

---

## Deliverables (expected)

- `infra/terraform/gcp/`
- `docs/runbooks/gcp_stage_deploy.md`

---

## Out of scope

- Multi-region HA.
- GPU node pool (Phase 7 PS7.x).
