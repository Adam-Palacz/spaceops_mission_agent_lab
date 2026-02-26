# ops-config

Operational configuration target for **GitOps PRs** from the SpaceOps agent (S2.2, S2.6). Contains alert thresholds, channel lists, and other deployable config that the agent may propose via pull requests.

## Layout

- **Subtree vs separate repo:** This directory is maintained as a **subtree** inside the main repo (`ops-config/` at repo root). It is structured so it can be split into a standalone Git repo later (e.g. `git subtree split -P ops-config`) if desired; it has no dependency on parent repo code.
- **Default branch:** `main`. The GitOps MCP creates feature branches (e.g. `agent/incident-123`) and opens PRs into `main`.
- **Path for agent/PR:** When using the subtree, the GitOps MCP targets the **local path** `ops-config/` (or `./ops-config` relative to repo root). If split to a separate repo, use that repo’s clone URL and auth (e.g. `GITHUB_TOKEN`).

## Contents

| Path | Description |
|------|-------------|
| `alerts/thresholds.yaml` | Alert thresholds (e.g. voltage, temperature) used by mission rules. |
| `channels/channel_list.yaml` | Telemetry channel names and metadata (optional reference for agent). |

## How the agent uses this (S2)

- **Safe actions:** Agent can create a PR that adds or edits files under `ops-config/` (e.g. change a threshold in `alerts/thresholds.yaml`).
- **Restricted actions:** After OPA allow and human approval, the approved action may create a PR here (S2.6).
- Branch protection on `main` is optional for MVP; recommended once in production.

## Testing create_pr (GitOps MCP)

1. **Optional (full PR flow):** In `.env` set `GITHUB_TOKEN` (repo scope) and `GITHUB_REPO` (e.g. `owner/repo` or `https://github.com/owner/repo`). Leave empty to test local-only (files written under `ops-config/`, no push/PR).

2. **Start the GitOps MCP server** from repo root:
   ```bash
   PYTHONPATH=. python -m apps.mcp.gitops_server.main
   ```
   Server listens on port 8004.

3. **In another terminal**, from repo root run the test script:
   ```bash
   PYTHONPATH=. python scripts/test_gitops_pr.py
   ```
   This calls `create_pr` with a test branch and file; the script prints the result (`note`, `pr_url`, or `push_error`).

4. **Verify:** Without token/repo you should see files under `ops-config/alerts/` (e.g. `test_threshold.yaml`). With token/repo set, a branch is pushed and a PR is created; check the repo on GitHub.
