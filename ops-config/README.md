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
