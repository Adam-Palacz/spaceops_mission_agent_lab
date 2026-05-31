# Variant B - agent opens a PR, Argo deploys ops-config

End-to-end: **gitops-mcp `create_pr`** -> GitHub PR -> merge -> **Argo CD** sync ConfigMap -> API sees the new configuration.

```
Agent / test script → gitops-mcp → GitHub PR (ops-config/)
       merge main → Argo spaceops-ops-config → ConfigMap
                  → Argo spaceops-stage → Helm (API mount ConfigMap)
```

---

## Requirements

| Element | Setting |
|---------|------------|
| Argo CD | `make gitops-install` + `make gitops-bootstrap` |
| Stage Secret | `GITHUB_TOKEN` (repo scope) in `spaceops-stage-secrets` |
| Env gitops-mcp | `GITHUB_REPO=Adam-Palacz/spaceops_mission_agent_lab` (Helm `gitopsMcp.githubRepo`) |
| Helm handoff | `make gitops-handoff` if the release was previously managed by imperative `helm upgrade` |
| After merge | `python scripts/render_ops_config_kustomize.py` + commit (new files in ops-config) |

---

## 1. Secret + redeploy (GITHUB_TOKEN)

```powershell
# .env or manual export:
$env:GITHUB_TOKEN = "ghp_..."
$env:K8S_NAMESPACE = "spaceops-stage"
$env:K8S_SECRET_NAME = "spaceops-stage-secrets"
# + POSTGRES_PASSWORD, OPENAI_API_KEY as before
.venv\Scripts\python.exe scripts\k8s_secrets_bootstrap.py

$env:GCP_PROJECT_ID = "spaceops-project"
make gcp-stage-deploy --skip-secrets  # or Helm with values-stage-full
```

---

## 2. Argo CD (Git + main branch after merge)

```powershell
$env:GITOPS_REPO_URL = "https://github.com/Adam-Palacz/spaceops_mission_agent_lab.git"
$env:GITOPS_TARGET_REVISION = "main"
make gitops-bootstrap
make gitops-handoff   # one-time: hand the Helm release over to Argo
make gitops-status
```

Argo applications:

| App | Wave | What it syncs |
|-----|------|------------|
| `spaceops-ops-config` | 0 | ConfigMap from `ops-config/` |
| `spaceops-stage` | 1 | Helm (API mount ConfigMap) |

---

## 3. Agent / script opens PR

**Option A - test script (port-forward gitops-mcp):**

```powershell
kubectl port-forward -n spaceops-stage svc/spaceops-gitops-mcp 8004:8004

$env:GITOPS_MCP_URL = "http://localhost:8004/mcp"
$env:GITHUB_REPO = "Adam-Palacz/spaceops_mission_agent_lab"
$env:GITHUB_TOKEN = "ghp_..."
.venv\Scripts\python.exe scripts\test_gitops_pr.py
```

Result: `pr_url: https://github.com/.../pull/N`

**Option B - agent through API** (incident with a `create_pr` plan step, OPA allow):

```powershell
# POST /runs with a payload that leads to create_pr (see portfolio / evals)
$BASE = "http://<LB-IP>:8000"
# ...
```

---

## 4. Merge PR → Argo deploy

1. **Merge** PR na GitHubie (`main`).
2. If the agent added a **new** YAML file under `ops-config/`:

   ```powershell
   python scripts/render_ops_config_kustomize.py
   git add deploy/gitops/ops-config-kustomize/ deploy/helm/spaceops/values-ops-config-mounts.yaml
   git commit -m "chore: refresh ops-config kustomize and Helm mount items"
   git push
   ```

   (Editing an existing file, e.g. `thresholds.yaml`, does not require regeneration.)

3. Argo auto-sync (~1–3 min) lub:

   ```powershell
   make gitops-rollout-demo GITOPS_DEMO_ARGS=--sync-only
   ```

4. **Restart API** (ConfigMap mount — brak hot-reload):

   ```powershell
   kubectl rollout restart deploy/spaceops-api -n spaceops-stage
   kubectl rollout status deploy/spaceops-api -n spaceops-stage
   ```

5. **Verification:**

   ```powershell
   kubectl get configmap spaceops-ops-config -n spaceops-stage -o yaml
   kubectl exec -n spaceops-stage deploy/spaceops-api -- cat /app/ops-config/alerts/test_threshold.yaml
   ```

---

## 5. Rollback

`git revert` merge commit -> push -> Argo sync -> restart API (as above).

---

## Technical notes

- The MCP image **does not have `.git`** - `create_pr` uses the **GitHub API** (not local `git push`).
- Helm values / image tag: still `values-gitops-stage.yaml`; **ops-config**: separate Application.
- Prod: same pattern; **manual** sync on `spaceops-prod` (ADR 0005).

---

## Related

- [gitops_bootstrap.md](gitops_bootstrap.md)
- [ops-config/README.md](../../ops-config/README.md)
- [ADR 0008](../adr/0008-gitops-argocd.md)
