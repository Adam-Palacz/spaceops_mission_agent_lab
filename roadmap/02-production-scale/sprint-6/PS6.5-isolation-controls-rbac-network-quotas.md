# PS6.5 — Isolation controls (RBAC, network, quotas)

| Field | Value |
|-------|-------|
| **Task ID** | PS6.5 |
| **Status** | Todo |

---

## Description

Implement **logical isolation** for `dev` / `stage` / `prod` on a shared cluster: namespaces, RBAC,
NetworkPolicy, ResourceQuota, LimitRange. Matches Phase 6 “shared compute, isolated tenants” model.

---

## Requirements

- [ ] Separate **namespaces** per environment (names from PS6.1 ADR).
- [ ] **ServiceAccounts** per workload; minimal RBAC (no cluster-admin for app SA).
- [ ] **NetworkPolicy:** default deny between env namespaces; allow only required paths (api→postgres,
      api→opa, worker→mcp, egress to LLM endpoints documented).
- [ ] **ResourceQuota** + **LimitRange** per namespace (prevent dev starving stage).
- [ ] Document what is **not** isolated (shared control plane, shared nodes) vs what is.
- [ ] Optional: Kyverno/Gatekeeper policy stub for “no `:latest` tag in prod” (design note acceptable).

---

## Dependencies

- **PS6.1** — namespace naming and env boundaries.
- **PS6.3** — manifests accept namespace and SA wiring.

---

## Checklist

- [ ] Policy manifests in deploy package (PS6.3).
- [ ] Runbook: verify isolation (`kubectl auth can-i`, cross-namespace curl should fail).
- [ ] Test script or doc steps for quota enforcement (optional automated test).

---

## Test / acceptance

- [ ] Pod in `dev` cannot reach postgres Service in `prod` namespace (NetworkPolicy).
- [ ] App ServiceAccount cannot patch cluster-scoped resources.
- [ ] Reviewer checklist in runbook passes on local cluster.

---

## Deliverables (expected)

- `deploy/helm/spaceops/templates/networkpolicy.yaml` (or equivalent Helm template path)
- `docs/runbooks/k8s_environment_isolation.md`

---

## Out of scope

- Service mesh mTLS (backlog idea in parent roadmap).
