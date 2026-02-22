# BL-002 — README per folder

**Backlog item** — use this spec to create a sprint task (e.g. P4.x or a dedicated sprint task) when you schedule this work. The backlog has no statuses.

| Field | Value |
|-------|--------|
| **Backlog ID** | BL-002 |
| **Source** | Improves onboarding and docs (NF7); aligns with repo structure in [docs/architecture/repo_structure.mmd](../../docs/architecture/repo_structure.mmd). |

---

## Description

**Objective:** Add a short README.md to every meaningful folder in the repo so that anyone (or AI) opening a directory understands its role, what lives there, and how it relates to the rest of the project.

Each README should be concise (a few lines to one short section): purpose of the folder, main files or subfolders, and optionally a link to the relevant docs or roadmap task. No need for long prose; consistency and coverage matter more.

---

## Requirements

- [ ] Every folder that is part of the project layout (apps/, data/, kb/, evals/, infra/, docs/, roadmap/, and their subfolders as in repo structure) has a README.md unless it is a leaf that already has a single obvious file (e.g. a folder containing only one script).
- [ ] README content: at minimum, one sentence on the folder’s purpose; optionally list main files or subfolders and a link to goals.md, project_doc.md, or a roadmap task.
- [ ] Root README and docs/README stay as they are; this task adds or completes READMEs in **other** folders (e.g. apps/api, apps/agent, apps/mcp/*, data/*, kb/*, evals, infra, roadmap/*).
- [ ] Format: Markdown; same language as the rest of the repo (English).

---

## Checklist

- [ ] List target folders from repo structure (e.g. apps, apps/api, apps/agent, apps/mcp, apps/mcp/telemetry_server, apps/mcp/kb_server, data, data/telemetry, data/events, data/ground_logs, data/incidents, kb, kb/runbooks, kb/postmortems, kb/policies, evals, infra, roadmap, roadmap/01-core, roadmap/02-hardening, roadmap/backlog; docs subfolders if desired).
- [ ] For each folder: add README.md with purpose and, if useful, pointer to docs or roadmap.
- [ ] Skip folders that are empty placeholders with only .gitkeep unless a one-line README is useful.
- [ ] Ensure no broken links; optionally add a single “README index” or note in docs/README that folder READMEs exist.

---

## Test requirements

- Every listed folder contains a README.md file.
- A new contributor can open any folder and understand its role from the README.
- READMEs do not duplicate large blocks from root or docs; they are short and folder-specific.
