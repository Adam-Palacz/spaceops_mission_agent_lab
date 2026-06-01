# PS7.1 — Live stage GKE deploy

| Field | Value |
|-------|--------|
| **Task ID** | PS7.1 |
| **Status** | Todo |
| **Source** | PS6.8 stretch; [gcp_stage_deploy.md](../../../docs/runbooks/gcp_stage_deploy.md) |

## Description

Reproducible deploy of SpaceOps to **stage GKE** with Terraform + Helm (`values-gcp-stage.yaml`).
Proof: demo scenarios A/B with trace and evidence in cloud.

## Requirements

- [ ] `terraform apply` on stage project (documented vars).
- [ ] Stage variables use a small quota-safe node shape (`node_locations`, disk size/type) and avoid surprise regional 3x100GB defaults.
- [ ] Helm install with secrets via ESO/SOPS path (no plain-text in Git).
- [ ] Ingress/LB for API; UI optional.
- [ ] Runbook: destroy/recreate time-boxed.

## Acceptance

- [ ] Operator completes runbook flow without ad-hoc steps.
- [ ] Scenarios A and B from `docs/portfolio/README.md` pass on stage.
- [ ] `terraform plan` does not propose replacing a healthy cluster unless the operator intentionally taints/destroys it.
- [ ] GCP troubleshooting notes cover SSD quota exhaustion, failed cluster operations, and safe recovery (`terraform untaint` / recreate decision).

## Live GCP lessons to capture

- Regional GKE can multiply node disk usage across zones; pin `node_locations` for the lab stage cluster.
- Keep node disk size/type explicit in Terraform to avoid quota failures on small projects.
- Treat a tainted but healthy cluster as a recovery decision, not an automatic destroy/recreate path.
