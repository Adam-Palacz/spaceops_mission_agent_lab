# PS6.5 — Isolation controls (RBAC, network, quotas)

| Field | Value |
|-------|-------|
| **Task ID** | PS6.5 |
| **Status** | Done |

---

## Description

Implement **logical isolation** for `dev` / `stage` / `prod` on a shared cluster: namespaces, RBAC,
NetworkPolicy, ResourceQuota, LimitRange. Matches Phase 6 “shared compute, isolated tenants” model.

---

## Requirements

- [x] Separate **namespaces** per environment (names from PS6.1 ADR).
- [x] **ServiceAccounts** per workload; minimal RBAC (no cluster-admin for app SA).
- [x] **NetworkPolicy:** default deny between env namespaces; allow only required paths (api→postgres,
      api→opa, worker→mcp, egress to LLM endpoints documented).
- [x] **ResourceQuota** + **LimitRange** per namespace (prevent dev starving stage).
- [x] Document what is **not** isolated (shared control plane, shared nodes) vs what is.
- [x] Optional: Kyverno/Gatekeeper policy stub for “no `:latest` tag in prod” (design note acceptable).

---

## Dependencies

- **PS6.1** — namespace naming and env boundaries.
- **PS6.2** — manifests accept namespace and SA wiring.

---

## Checklist

- [x] Policy manifests in deploy package (PS6.2).
- [x] Runbook: verify isolation (`kubectl auth can-i`, cross-namespace curl should fail).
- [x] Test script or doc steps for quota enforcement (optional automated test).

---

## Test / acceptance

- [x] Pod in `dev` cannot reach postgres Service in `prod` namespace (NetworkPolicy) — `make k8s-isolation-verify` after `make k8s-up` (Calico on kind by default).
- [x] App ServiceAccount cannot patch cluster-scoped resources.
- [x] Reviewer checklist in runbook passes on local cluster.

---

## Deliverables (expected)

- `deploy/helm/spaceops/templates/networkpolicy.yaml`
- `deploy/helm/spaceops/templates/resourcequota.yaml`, `limitrange.yaml`, `rbac.yaml`, `isolation-serviceaccounts.yaml`
- `docs/runbooks/k8s_environment_isolation.md`
- `scripts/k8s_isolation_verify.py` + `make k8s-isolation-verify`
- `deploy/policy/kyverno/README.md` (design stub)
- `scripts/k8s_cluster_cni.py` — Calico install for local kind
- `infra/k8s/local/kind-config.yaml` — `disableDefaultCNI` + Calico pod subnet

---

## Out of scope

- Service mesh mTLS (backlog idea in parent roadmap).
