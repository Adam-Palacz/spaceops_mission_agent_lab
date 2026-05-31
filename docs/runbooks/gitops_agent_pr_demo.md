# Wariant B — agent otwiera PR, Argo wdraża ops-config

End-to-end: **gitops-mcp `create_pr`** → GitHub PR → merge → **Argo CD** sync ConfigMap → API widzi nową konfigurację.

```
Agent / test script → gitops-mcp → GitHub PR (ops-config/)
       merge main → Argo spaceops-ops-config → ConfigMap
                  → Argo spaceops-stage → Helm (API mount ConfigMap)
```

---

## Wymagania

| Element | Ustawienie |
|---------|------------|
| Argo CD | `make gitops-install` + `make gitops-bootstrap` |
| Secret stage | `GITHUB_TOKEN` (repo scope) w `spaceops-stage-secrets` |
| Env gitops-mcp | `GITHUB_REPO=Adam-Palacz/spaceops_mission_agent_lab` (Helm `gitopsMcp.githubRepo`) |
| Handoff Helm | `make gitops-handoff` jeśli wcześniej imperatywny `helm upgrade` |
| Po merge | `python scripts/render_ops_config_kustomize.py` + commit (nowe pliki w ops-config) |

---

## 1. Secret + redeploy (GITHUB_TOKEN)

```powershell
# .env lub ręcznie:
$env:GITHUB_TOKEN = "ghp_..."
$env:K8S_NAMESPACE = "spaceops-stage"
$env:K8S_SECRET_NAME = "spaceops-stage-secrets"
# + POSTGRES_PASSWORD, OPENAI_API_KEY jak wcześniej
.venv\Scripts\python.exe scripts\k8s_secrets_bootstrap.py

$env:GCP_PROJECT_ID = "spaceops-project"
make gcp-stage-deploy --skip-secrets  # lub helm z values-stage-full
```

---

## 2. Argo CD (Git + branch main po merge)

```powershell
$env:GITOPS_REPO_URL = "https://github.com/Adam-Palacz/spaceops_mission_agent_lab.git"
$env:GITOPS_TARGET_REVISION = "main"
make gitops-bootstrap
make gitops-handoff   # jednorazowo: oddaj release Helm Argo
make gitops-status
```

Aplikacje Argo:

| App | Wave | Co syncuje |
|-----|------|------------|
| `spaceops-ops-config` | 0 | ConfigMap z `ops-config/` |
| `spaceops-stage` | 1 | Helm (API mount ConfigMap) |

---

## 3. Agent / skrypt otwiera PR

**Opcja A — skrypt testowy (port-forward gitops-mcp):**

```powershell
kubectl port-forward -n spaceops-stage svc/spaceops-gitops-mcp 8004:8004

$env:GITOPS_MCP_URL = "http://localhost:8004/mcp"
$env:GITHUB_REPO = "Adam-Palacz/spaceops_mission_agent_lab"
$env:GITHUB_TOKEN = "ghp_..."
.venv\Scripts\python.exe scripts\test_gitops_pr.py
```

Wynik: `pr_url: https://github.com/.../pull/N`

**Opcja B — agent przez API** (incydent z krokiem `create_pr` w planie, OPA allow):

```powershell
# POST /runs z payloadem prowadzącym do create_pr (patrz portfolio / evals)
$BASE = "http://<LB-IP>:8000"
# ...
```

---

## 4. Merge PR → Argo deploy

1. **Merge** PR na GitHubie (`main`).
2. Jeśli agent dodał **nowy** plik YAML w `ops-config/`:

   ```powershell
   python scripts/render_ops_config_kustomize.py
   git add deploy/gitops/ops-config-kustomize/kustomization.yaml
   git commit -m "chore: refresh ops-config kustomize"
   git push
   ```

   (Edycja istniejącego pliku, np. `thresholds.yaml`, nie wymaga regen.)

3. Argo auto-sync (~1–3 min) lub:

   ```powershell
   make gitops-rollout-demo GITOPS_DEMO_ARGS=--sync-only
   ```

4. **Restart API** (ConfigMap mount — brak hot-reload):

   ```powershell
   kubectl rollout restart deploy/spaceops-api -n spaceops-stage
   kubectl rollout status deploy/spaceops-api -n spaceops-stage
   ```

5. **Weryfikacja:**

   ```powershell
   kubectl get configmap spaceops-ops-config -n spaceops-stage -o yaml
   kubectl exec -n spaceops-stage deploy/spaceops-api -- cat /app/ops-config/alerts/test_threshold.yaml
   ```

---

## 5. Rollback

`git revert` merge commit → push → Argo sync → restart API (jak wyżej).

---

## Uwagi techniczne

- Obraz MCP **nie ma `.git`** — `create_pr` używa **GitHub API** (nie lokalnego `git push`).
- Helm values / image tag: nadal `values-gitops-stage.yaml`; **ops-config**: osobna Application.
- Prod: ten sam wzorzec; sync **manualny** na `spaceops-prod` (ADR 0005).

---

## Powiązane

- [gitops_bootstrap.md](gitops_bootstrap.md)
- [ops-config/README.md](../../ops-config/README.md)
- [ADR 0008](../adr/0008-gitops-argocd.md)
