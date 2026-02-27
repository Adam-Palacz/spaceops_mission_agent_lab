# Sprint 3 — Technical Debt Management (Weeks 5–6)

**Goal:** Systematically reduce and control technical debt in four areas: LLM/prompt lifecycle,
resiliency patterns, infra/sec hygiene, and process. Make future feature work safer and cheaper
by putting in place the core scaffolding for model upgrades, prompt management, retries/chaos,
dependency hygiene, secrets, and a recurring tech-debt budget.

---

## Outcomes

- Model + prompt lifecycle is explicit: there is a place and process for upgrading models,
  versioning prompts, and keeping context usage under control.
- Core network paths (MCP, HTTP clients) have reusable retry/backoff and circuit-breaker patterns,
  and there is a basic chaos/degradation harness for testing fail-closed behaviour.
- Dependency and secrets management have a documented plan and initial automation (updates + IaC
  direction + secrets backend integration path), rather than staying as one-off tasks.
- Process-level guardrail: a documented, enforceable “tech-debt budget” pattern per sprint.

---

## Tasks

See **[BOARD.md](BOARD.md)** for status. Each task has a detail file: `S3.x-short-name.md`.
Tasks are sized so they can be pulled into future sprints as needed if Sprint 3 is only
partially executed.

---

## Definition of done (sprint)

- [ ] At least one concrete mechanism for **model upgrade/shadow testing** is implemented and
      documented (even if limited to current LLM provider).
- [ ] Prompts are no longer only “buried in code”; there is a **prompt registry** or configuration
      layer with basic versioning semantics.
- [ ] MCP / external HTTP calls use a shared **retry/backoff + circuit breaker** helper, and there
      is at least one **chaos/degradation scenario** that proves fail-closed behaviour (escalation
      instead of unsafe action).
- [ ] Dependency update automation is configured (Dependabot/Renovate or equivalent) and gated by
      tests/evals.
- [ ] A short **Tech Debt Management** section exists in docs/README that explains the 20% budget
      rule and how to propose/refine debt tasks.

---

## Instructions for AI

- Do not modify Sprint 1 or Sprint 2 scope; Sprint 3 builds on top of them to harden the system.
- For each S3.x task: open `S3.x-*.md`, follow Requirements and Checklist, run Test requirements,
  then update status in **BOARD.md**.
- When implementing infra-focused tasks (Dependabot/Renovate, IaC, secrets), prioritise clear,
  minimal configurations and documentation over full cloud rollout. The goal is a **solid
  foundation**, not maximal feature coverage in one sprint.

