# Automated dependency updates (S3.6)

This repo uses **GitHub Dependabot** to propose regular dependency updates. All update PRs
must pass **lint, tests, and evals** before being merged.

## Configuration

- Config file: `.github/dependabot.yml`.
- Package ecosystems watched:
  - **pip** — `requirements.txt` in the repo root.
  - **github-actions** — Actions used in `.github/workflows/`.
- Schedule: **weekly** (Sunday for pip; weekly for Actions).
- Dependabot opens PRs with the `dependencies` label and commit prefix `deps:` / `deps(actions):`.

## CI on dependency PRs

The `CI` workflow (`.github/workflows/ci.yml`) already runs on every PR to `main`:

- **lint**: `ruff`, `mypy`,
- **test**: `pytest tests/ -v`,
- **evals**: `python -m evals.scoring` (with Telemetry MCP server).

Any Dependabot PR automatically triggers these jobs. A dependency update PR is **mergeable**
only when all three jobs are green.

## Review policy

When reviewing dependency update PRs:

- Check that **all CI jobs are green**:
  - lint (no new type/lint issues),
  - pytest (no failing unit tests),
  - evals (standard cases + injection suite all PASS).
- If **evals fail** (behavioural regression), do **not merge** the PR until:
  - the underlying issue is fixed, or
  - the version bump is adjusted/rolled back.
- Prefer merging smaller, frequent updates over large, infrequent jumps.

This ensures we benefit from security/bugfix releases while keeping the agent’s behaviour
under control via evals.

