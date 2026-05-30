# Kubernetes environment isolation (PS6.5)

Logical isolation for **`spaceops-dev`**, **`spaceops-stage`**, and **`spaceops-prod`** on a
**shared cluster** (ADR 0005). Implemented in the Helm chart; enabled in env overlays
(`values-dev.yaml`, `values-stage.yaml`, `values-prod.yaml`).

## What is isolated vs shared

| Isolated (per namespace) | Shared (Phase 6 default) |
|--------------------------|---------------------------|
| Pods, Services, Secrets, ConfigMaps | Kubernetes control plane |
| Network traffic to other env namespaces | Worker nodes (unless taints/GPU pools) |
| ResourceQuota / LimitRange budgets | Container runtime (Docker/containerd) |
| ServiceAccounts (no K8s API access) | Cluster DNS (kube-system) |

**Not in scope:** service mesh mTLS, dedicated clusters (Phase 7 upgrade path in ADR 0005).

---

## Controls shipped in Helm

| Control | Template | Purpose |
|---------|----------|---------|
| **Namespace labels** | `namespace.yaml` | `spaceops.io/environment: dev\|stage\|prod` |
| **ServiceAccounts** | `isolation-serviceaccounts.yaml` | One SA per enabled workload |
| **NetworkPolicy** | `networkpolicy.yaml` | Same-namespace traffic + DNS; block cross-env |
| **ResourceQuota** | `resourcequota.yaml` | Cap CPU/memory/pods per env |
| **LimitRange** | `limitrange.yaml` | Default container requests/limits |
| **RBAC** | `rbac.yaml` | Read-only Role for operators; **no binding** for app SAs |

### Network paths allowed (in-namespace)

| From | To | Notes |
|------|-----|-------|
| `api` | `postgres`, `opa`, MCPs, `nats`, `otel-collector` | ClusterIP Services |
| `telemetry-persister` | `postgres`, `nats` | Minimal profile |
| `api` | External `:443` | When `allowLlmEgress: true` (OpenAI / HTTPS LLM) |
| All pods | `kube-system` DNS `:53` | Name resolution |

Cross-namespace traffic is **not** allowed (no rule permitting other namespaces).

Toggle in values:

```yaml
isolation:
  enabled: true
  environment: dev
  networkPolicy:
    enabled: true
    allowLlmEgress: true
```

---

## Apply / upgrade on local kind

Local kind bootstraps **Calico** automatically (`disableDefaultCNI` in
`infra/k8s/local/kind-config.yaml`) so NetworkPolicy rules are **enforced**, not just rendered.

**Migrating from an older kindnet cluster:** recreate once:

```powershell
make k8s-down
make k8s-up
```

Skip Calico only for faster lab without network proof:

```powershell
$env:K8S_SKIP_CALICO = "1"
make k8s-up
```

After chart change on an existing Calico-backed cluster:

```powershell
$env:K8S_SKIP_BUILD = "1"
make k8s-up
```

Verify (full cross-namespace check when Calico is installed):

```powershell
make k8s-isolation-verify
```

---

## Manual verification checklist

> **NetworkPolicy enforcement** requires a capable CNI (Calico, Cilium, Antrea, Weave, Canal).
> **`make k8s-up`** installs Calico on new kind clusters by default. Legacy kindnet-only clusters
> must be recreated (`make k8s-down && make k8s-up`). Use
> `K8S_ISOLATION_ARGS=--skip-cross-ns make k8s-isolation-verify` only when Calico was skipped
> (`K8S_SKIP_CALICO=1`).

### 1. Resources exist

```bash
kubectl get networkpolicy,resourcequota,limitrange,role,serviceaccount -n spaceops-dev
kubectl get namespace spaceops-dev --show-labels
```

Expect label `spaceops.io/environment=dev`.

### 2. App SA cannot manage cluster

```bash
kubectl auth can-i patch nodes \
  --as=system:serviceaccount:spaceops-dev:spaceops-api
# no
```

### 3. Cross-namespace blocked

```bash
# Automated (creates temporary probe namespace):
make k8s-isolation-verify

# Manual: from API pod, curl Service in another namespace — should fail/timeout
kubectl run -n spaceops-prod-isolation-probe probe --image=nginx --port=80
kubectl exec -n spaceops-dev deploy/spaceops-api -- python -c \
  "import socket; socket.create_connection(('probe.spaceops-prod-isolation-probe.svc.cluster.local',80),2)"
```

### 4. Same-namespace still works

```bash
make k8s-smoke
kubectl exec -n spaceops-dev deploy/spaceops-api -- python -c \
  "import socket; socket.create_connection(('spaceops-postgres',5432),2); print('ok')"
```

### 5. Quota visible

```bash
kubectl describe resourcequota -n spaceops-dev
kubectl describe limitrange -n spaceops-dev
```

---

## Reviewer checklist (PS6.5 acceptance)

- [ ] Three namespace names match ADR 0005 (`spaceops-dev`, `spaceops-stage`, `spaceops-prod`)
- [ ] `isolation.enabled: true` in dev/stage/prod overlays
- [ ] Workload pods use component ServiceAccounts (`spaceops-api`, not default)
- [ ] App ServiceAccount **cannot** `patch nodes` / `create clusterrolebindings`
- [ ] Cross-namespace probe fails (`make k8s-isolation-verify`)
- [ ] `make k8s-smoke` passes after isolation enabled
- [ ] ResourceQuota limits documented per env overlay

---

## Admission policy (optional — design stub)

Kyverno/Gatekeeper policies (e.g. **no `:latest` in prod**) are documented but **not installed**
by default: [deploy/policy/kyverno/README.md](../../deploy/policy/kyverno/README.md).

PS6.7 GitOps bootstrap should reference the same rollback/isolation semantics.

---

## Related

- [ADR 0005 — Environment strategy](../adr/0005-environment-strategy-dev-stage-prod.md)
- [Environment promotion](environment_promotion.md)
- [Local K8s dev (PS6.3)](local_k8s_dev.md)
- [Helm chart README](../../deploy/helm/spaceops/README.md)
