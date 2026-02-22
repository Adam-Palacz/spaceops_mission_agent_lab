# SpaceOps Mission Agent Lab — Mermaid diagrams

This file is the **index and entry point** for all Mermaid diagrams in `docs/`. Diagrams are stored as **.mmd** files in subfolders by domain. Use a Mermaid-compatible viewer (VS Code Mermaid extension, GitHub/GitLab, [Mermaid Live](https://mermaid.live)) to render them.

---

## Role of `docs/` in the project

The **docs/** directory holds project documentation that supports both humans and AI tooling:

- **README.md** (this file) — Index of Mermaid diagrams; start here when looking for a flow, architecture, or schema.
- **workflow/** — High-level pipeline (Ingest → … → Post-incident) and escalation path; aligns with `project_doc.md` §4 and `goals.md` F1–F10.
- **architecture/** — System boundaries (API, Agent, MCP, OPA, storage, observability), repo layout, and production-ready criteria from `goals.md` §4.5.
- **agent/** — LangGraph state machine and Act logic (safe vs restricted, OPA, approval); implements behaviour described in `roadmap_F1.md` and policy in `goals.md` §4.3.
- **planning/** — Sprint and phase roadmap (S1, S2, Phase 4) and epic→deliverable mapping; mirrors `roadmap_F1.md`.
- **requirements/** — How goals decompose into Functional, Non-functional, Policy, and MoE/MoP; references `goals.md` §4.
- **data/** — Audit log event schema (append-only, immutable); matches `goals.md` §4.6.

**Cross-references for AI:** When answering questions about pipeline, architecture, agent behaviour, roadmap, or requirements, use this index to locate the right .mmd; the canonical text remains in `goals.md`, `project_doc.md`, and `roadmap_F1.md` at repo root.

---

## Folder structure

| Folder | Purpose | Key concepts |
|--------|---------|--------------|
| **[workflow/](workflow/)** | End-to-end pipeline and escalation | Ingest, Triage, Investigate, Decide, Act, Report, Post-incident; when to escalate (confidence, evidence, timeout, OPA error). |
| **[architecture/](architecture/)** | System shape and repo layout | FastAPI, LangGraph, MCP servers (Telemetry, KB, Ticketing, GitOps), OPA, Postgres/pgvector, DuckDB, data/, kb/, ops-config, OTel/Jaeger/Prometheus/Grafana; single-command run, pinned deps, structured logging. |
| **[agent/](agent/)** | Agent state and Act behaviour | LangGraph nodes (Triage → Investigate → Decide → Act → Report); Escalation state; safe vs restricted steps; OPA allow/deny/error; approval request and execution. |
| **[planning/](planning/)** | Delivery plan | Sprint 1 (pipeline to Report + evals + OTel), Sprint 2 (Act + OPA + approvals + injection suite), Phase 4 (docs, runbooks, expanded evals). |
| **[requirements/](requirements/)** | Goals and measures | Functional (F1–F10), Non-functional (NF1–NF9), Policy (P1–P6); MoE (triage accuracy, citation precision, unsafe=0, escalation); MoP (latency, tool-call count). |
| **[data/](data/)** | Audit and schema | Audit log: timestamp, trace_id, incident_id, actor, tool, args_hash, decision, policy_result, outcome; append-only, no in-place edits. |

---

## Index of diagrams

### Workflow
| Diagram | File | Use when |
|---------|------|----------|
| End-to-end pipeline | [workflow/end_to_end_pipeline.mmd](workflow/end_to_end_pipeline.mmd) | Explaining the full flow from ingest to post-incident. |
| Pipeline with escalation path | [workflow/pipeline_with_escalation.mmd](workflow/pipeline_with_escalation.mmd) | Showing when the agent escalates (confidence/evidence/timeout/OPA) and hands off to Report. |

### Architecture
| Diagram | File | Use when |
|---------|------|----------|
| System architecture (components) | [architecture/system_architecture.mmd](architecture/system_architecture.mmd) | Describing components, data flow, and observability. |
| Repository structure | [architecture/repo_structure.mmd](architecture/repo_structure.mmd) | Explaining directory layout (apps/, data/, kb/, evals/, infra/). |
| Production-ready criteria | [architecture/production_ready_criteria.mmd](architecture/production_ready_criteria.mmd) | Checking or explaining "production-ready" (single command, fixtures, evals, lockfile, logging). |

### Agent
| Diagram | File | Use when |
|---------|------|----------|
| LangGraph state flow | [agent/langgraph_state_flow.mmd](agent/langgraph_state_flow.mmd) | Describing agent states and transitions, including to Escalation. |
| Act flow: safe vs restricted | [agent/act_flow_safe_restricted.mmd](agent/act_flow_safe_restricted.mmd) | Explaining how safe steps execute vs restricted (OPA → approval → execute or deny + escalation). |

### Planning
| Diagram | File | Use when |
|---------|------|----------|
| Roadmap: sprints and phase | [planning/roadmap_sprints.mmd](planning/roadmap_sprints.mmd) | Showing S1 → S2 → Phase 4 and what each delivers. |
| Epic and deliverable summary | [planning/epic_deliverable_summary.mmd](planning/epic_deliverable_summary.mmd) | Mapping epics (E0, E1, E2) to deliverables. |

### Requirements
| Diagram | File | Use when |
|---------|------|----------|
| Requirements structure | [requirements/requirements_structure.mmd](requirements/requirements_structure.mmd) | Showing how goals break into F, NF, Policy, MoE. |
| MoE / MoP | [requirements/moe_mop.mmd](requirements/moe_mop.mmd) | Explaining effectiveness and performance measures (evals, dashboard). |

### Data / schema
| Diagram | File | Use when |
|---------|------|----------|
| Audit log event schema | [data/audit_log_schema.mmd](data/audit_log_schema.mmd) | Defining or implementing the audit log format (goals.md §4.6). |

---

## Updating diagrams

- When **goals**, **roadmap**, or **architecture** change, update the matching .mmd and, if needed, the descriptions in this file.
- Keep diagram IDs and labels consistent with terminology in `goals.md` and `project_doc.md` (e.g. "escalation packet", "fail-closed", "safe vs restricted").

---

## Maintenance

| Field | Value |
|-------|--------|
| **Document version** | 1.0 |
| **Last updated** | 2025-02-14 |

### Instructions for AI when working in `docs/`

1. **Keep index and folder in sync.** Before adding, removing, or renaming any `.mmd` in `docs/` or subfolders, read this README. After the change, update the "Folder structure" table and "Index of diagrams" so they match the actual files. No orphan rows (file removed but still in index); no missing rows (new .mmd not listed).

2. **One diagram = one .mmd.** New diagrams go in the right subfolder (`workflow/`, `architecture/`, `agent/`, `planning/`, `requirements/`, `data/`). Add one Index row under the right heading; keep Folder structure accurate.

3. **Canonical text is in repo root.** When changing behaviour or requirements, update `goals.md`, `project_doc.md`, or `roadmap_F1.md` first, then the relevant .mmd and this README if needed. Do not define requirements or process only in `docs/`.

4. **If unsure, list the folder.** When unsure which .mmd exist in a subfolder, list that folder (e.g. `docs/workflow/`) and then update this README so Index and Folder structure match.

5. **Bump version or date on substantive edits.** When you add a section, rework Maintenance, or change the index, set "Last updated" to today (YYYY-MM-DD) or bump "Document version".
