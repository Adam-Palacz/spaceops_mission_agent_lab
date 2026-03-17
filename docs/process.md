# Process: tech-debt budget (S3.8)

This document codifies the **tech-debt budget** for SpaceOps Mission Agent Lab and how it
is applied in sprint planning and reviews.

## 1. What counts as “tech debt work”

**Examples (count toward the budget):**

- Refactors that improve clarity or structure without adding new behaviour.
- Dead-code removal and simplification of complex branches.
- Improving test coverage for existing behaviour (no new features).
- Hardening / resilience work that pays back known tech debt (e.g. S3.4 retry/circuit breaker,
  S3.5 chaos harness, S3.6 automated dependency updates, S3.7 secrets abstraction).

**Non-examples (do _not_ count as tech debt work):**

- Shipping new user-visible features or APIs (even if they happen to clean things up).
- Adding new external integrations or MCPs.
- Large redesigns that introduce new scope (treat as normal epics/features).

Rule of thumb: if the primary goal is to **reduce future maintenance cost / risk** rather
than to add capability, it is tech-debt work.

## 2. Budget rule and tracking

- Target: **~20%** sprint capacity (tasks / story points) after S2 reserved for tech-debt.
- Tracking:
  - On sprint boards (`BOARD.md`), mark or group tasks that are “debt” items.
  - In issues/PRs, use a `tech-debt` label when appropriate.
- Example in Sprint 3:
  - S3.4 (HTTP/MCP retry & circuit breaker),
  - S3.5 (chaos / degradation harness),
  - S3.6 (automated dependency updates),
  - S3.7 (secrets management plan),
  - S3.8 (this process itself)
  all count toward the tech-debt budget.

## 3. Proposal / prioritisation

**How to propose a tech-debt task:**

- Create a roadmap task (`Sx.y-...md`) or backlog item that clearly states:
  - what debt is being paid down,
  - why it matters (risk / maintainability / performance),
  - how success is measured (tests, evals, reduced complexity).

**How it is prioritised vs features:**

- During sprint planning, aim for **at least one tech-debt item per sprint**, and
  roughly 20% of sprint capacity in total.
- If the sprint is feature-heavy, explicitly decide which debt items are deferred and
  record them in the backlog.

**Avoiding “stealth features”:**

- Tech-debt items should not introduce new externally visible behaviour without
  being treated as normal feature work.
- If a refactor unlocks a new capability, split it into:
  - one task for debt (refactor), and
  - one for the feature (new behaviour).

## 4. Surfacing the policy

- Main entry points:
  - `README.md` (docs table) links to this file.
  - `roadmap/01-core/README.md` can reference this process when planning future sprints.

## 5. Sprint planning snippet

When creating or updating a sprint board (`BOARD.md`), maintainers can add a short note
like this under the table:

```markdown
> Tech-debt budget: aim for ~20% of sprint capacity on debt items.
> For this sprint, the following tasks count as tech-debt: S3.4, S3.5, S3.6, S3.7, S3.8.
```

Future boards can adapt the list of task IDs as appropriate, but should keep the
**“~20% tech-debt”** reminder visible during planning and review.

