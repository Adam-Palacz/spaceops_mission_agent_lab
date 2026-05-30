# Kubernetes rollout and rollback (PS6.4)

Operator playbook for **Helm-based** deploy, rollback, and **LLM emergency rollback** on SpaceOps
clusters (local kind, stage, prod). Primary path: **imperative Helm**; GitOps (PS6.7) uses the same
semantics via Git revert + sync.

**Prerequisites:** PS6.2 chart installed; cluster context verified (`kubectl config current-context`).

---

## Strategy summary

| Topic | Choice | Notes |
|-------|--------|-------|
| **Primary deploy** | `helm upgrade --install` | Values overlays per env (ADR 0005) |
| **Atomic upgrades (lab/stage)** | `--atomic --wait` | Auto-rollback if readiness fails; portable across Helm 3.x and later |
| **Rollback (incident)** | `helm rollback` | Fast; uses revision history |
| **Rollback (GitOps)** | Git revert + sync | Same values outcome as `helm rollback` |
| **Image pin fallback** | `--set images.api.tag=…` | When chart unchanged, only image moved |
| **Canary (prod)** | Manual replica / values canary | Full blue/green deferred to Phase 7 |
| **LLM emergency** | Values patch only | `LLM_BACKEND=openai`; no app code deploy ([PS5.5](llm_backend_rollout.md)) |

---

## Standard deploy flow

### 1. Pre-checks

```bash
kubectl config current-context          # expect kind-spaceops-dev | stage | prod
kubectl get nodes
helm list -n spaceops-dev               # release must exist for upgrade
helm history spaceops -n spaceops-dev   # note current revision
kubectl get pods -n spaceops-dev        # all Running before change?
```

Confirm:

- [ ] Correct namespace (`spaceops-dev` | `spaceops-stage` | `spaceops-prod`)
- [ ] Secrets present (`kubectl get secret -n <ns>`)
- [ ] No stuck Helm release (`pending-*` / `failed` — see [Troubleshooting](#troubleshooting))
- [ ] CI green for the commit being deployed

### 2. Deploy

From repo root (local dev example):

```bash
helm upgrade --install spaceops deploy/helm/spaceops \
  --namespace spaceops-dev \
  --create-namespace \
  --atomic \
  --wait \
  --timeout 10m \
  -f deploy/helm/spaceops/values.yaml \
  -f deploy/helm/spaceops/values-dev.yaml \
  -f deploy/helm/spaceops/values-minimal-dev.yaml \
  --set secrets.postgresPassword=spaceops
```

**Stage / prod:** swap overlay file; never pass plaintext prod secrets on CLI — use PS6.6 refs.

### 3. Post-checks

```bash
helm status spaceops -n spaceops-dev
kubectl rollout status deployment/spaceops-api -n spaceops-dev
kubectl get pods -n spaceops-dev
make k8s-smoke                         # local: GET /health on :18000
```

### 4. Post-deploy smoke (recommended)

| Check | Command |
|-------|---------|
| **Health** | `curl http://127.0.0.1:8000/health` (after port-forward) |
| **Agent path** | `POST /runs` with test incident (needs `OPENAI_API_KEY` in Secret) |
| **Eval gate subset** | `make safety-gates` or CI parity job on promotion branch |
| **Traces** | With Jaeger profile enabled: port-forward UI, search `spaceops-api` service |

Port-forward:

```bash
kubectl port-forward -n spaceops-dev svc/spaceops-api 8000:8000
```

---

## Rollback flow

### Primary: `helm rollback`

```bash
helm history spaceops -n spaceops-dev
helm rollback spaceops <REVISION> -n spaceops-dev --wait --timeout 10m
kubectl rollout status deployment/spaceops-api -n spaceops-dev
make k8s-smoke
```

Use the **last known-good revision** from `helm history`. Document the revision number in the
incident note.

### Fallback A: GitOps revert (PS6.7)

1. Revert the commit that changed `values-stage.yaml` / image tag in Git.
2. Sync the Application (manual sync in prod per ADR 0005).
3. Verify same post-checks as above.

### Fallback B: Image pin (no chart change)

```bash
helm upgrade spaceops deploy/helm/spaceops \
  -n spaceops-dev \
  --reuse-values \
  --set images.api.tag=<known-good-tag> \
  --atomic --wait
```

---

## LLM emergency rollback (PS5.5 on K8s)

**Goal:** restore `openai` backend without rebuilding application images.

### Symptoms

- GPU/NIM unstable; gateway logs show `fallback_used=true` repeatedly
- Bad values set `api.llm.backend=gpu` without NIM profile

### Steps

1. **Patch values** (Helm):

```bash
helm upgrade spaceops deploy/helm/spaceops \
  -n spaceops-dev \
  --reuse-values \
  --set api.llm.backend=openai \
  --set nim.enabled=false \
  --wait --timeout 10m
```

2. **Restart API** if env did not roll (rare with Deployment spec change):

```bash
kubectl rollout restart deployment/spaceops-api -n spaceops-dev
kubectl rollout status deployment/spaceops-api -n spaceops-dev
```

3. **Verify env:**

```bash
kubectl get deployment spaceops-api -n spaceops-dev \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="LLM_BACKEND")].value}'
# expect: openai
```

4. **Scale GPU to zero:** ensure `nim.enabled=false` in values; no NIM pods running.

5. **Smoke:** `/health` + optional `POST /runs` — new calls should use `backend_actual=openai`.

Full policy: [llm_backend_rollout.md § Emergency rollback](llm_backend_rollout.md#emergency-rollback-no-code-deploy).

---

## Local demonstration

Requires running cluster from [local_k8s_dev.md](local_k8s_dev.md) (`make k8s-up`):

```bash
make k8s-rollout-demo
```

Script flow:

1. Pre-checks → baseline `/health`
2. `helm upgrade` with demo marker (`api.extraEnv.DEMO_ROLLOUT_VERSION=v2`) using `--atomic`
3. `helm rollback` to previous revision → `/health` OK
4. Simulate bad `LLM_BACKEND=gpu` → patch back to `openai` → verify env

---

## Incident capture template

When rolling back, record:

```markdown
## K8s deploy / rollback incident

- **Date / operator:**
- **Environment / namespace:**
- **Cluster context:** `kubectl config current-context`
- **Helm release:** spaceops
- **Revision before deploy:**
- **Revision after deploy (failed):**
- **Rollback revision used:**
- **Chart version / app commit:**
- **Values diff:** `helm get values spaceops -n <ns> --revision <N>` (store output)
- **Image tags:** api=… mcp=…
- **Symptom:** (e.g. CrashLoop, 500 on /runs, GPU fallback storm)
- **Trace IDs:** (from Jaeger or API logs)
- **LLM_BACKEND before / after:**
- **Resolution:** helm rollback | values patch | Git revert
- **Post-rollback smoke:** /health [ ]  POST /runs [ ]  safety-gates [ ]
- **Follow-up:** (parity report, PS6.6 secret rotation, etc.)
```

---

## Troubleshooting

| Symptom | Action |
|---------|--------|
| `another operation is in progress` | `helm status`; wait or `helm uninstall` if stuck `pending-*` |
| Rollback OK but pods old | `kubectl rollout restart deployment/spaceops-api` |
| `ImagePullBackOff` after rollback | Re-run `make k8s-up` or `kind load docker-image` |
| OPA CrashLoop after upgrade | Check ConfigMap mount; see PS6.3 fixes in chart |
| Atomic upgrade failed | Helm auto-reverted; inspect `helm history` and pod logs |

---

## Related

- [Environment promotion](environment_promotion.md)
- [LLM backend rollout (PS5.5)](llm_backend_rollout.md)
- [Local K8s dev (PS6.3)](local_k8s_dev.md)
- [Helm chart README](../../deploy/helm/spaceops/README.md)
- PS6.7 GitOps (when enabled): rollback = Git revert + sync, same revision semantics as above
