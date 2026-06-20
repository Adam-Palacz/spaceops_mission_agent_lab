# PS7.5 — README per folder (BL-002)

| Field | Value |
|-------|--------|
| **Task ID** | PS7.5 |
| **Status** | Done |
| **Backlog** | [BL-002](../../backlog/BL-002-readme-per-folder.md) |

## Description

Add short README.md files in uncovered folders (priority: `data/`, `kb/`, `evals/`, `infra/*`, `roadmap/02-production-scale`, `roadmap/03-next-gen-autonomy`).

## Folder checklist (repo)

| Area | Folders |
|------|---------|
| **data/** | `telemetry/`, `events/`, `ground_logs/`, `incidents/`, `replay/`, `replay/baselines/`, `replay/golden/` (+ runtime: `approvals/`, `llm_runs/`, `eval-reports/`, `replay/runs/`) |
| **kb/** | `runbooks/`, `postmortems/`, `policies/` |
| **evals/** | `fixtures/`, `fixtures/semantic/` (root + `injection_suite/`, `reports/` already had READMEs) |
| **infra/** | root, `opa/`, `sql/`, `k8s/`, `k8s/local/`, `terraform/`, `terraform/gcp/`, `grafana/` + provisioning subfolders |
| **roadmap/** | `02-production-scale/`, `03-next-gen-autonomy/` (sprint subfolders already covered) |

## Acceptance

- [x] Folder list in task checklist matches repo.
- [x] New contributor understands folder role in under 30 seconds.

## Verification

`tests/test_readme_per_folder_ps75.py` · index note in [docs/README.md](../../../docs/README.md).
