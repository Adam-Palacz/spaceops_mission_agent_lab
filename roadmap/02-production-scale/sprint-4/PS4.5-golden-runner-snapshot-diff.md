# PS4.5 — Golden runner snapshot/diff

| Field | Value |
|-------|-------|
| **Task ID** | PS4.5 |
| **Status** | Done |

---

## Description

Deepen golden-run workflows from PS2.8 into a repeatable runner that executes selected scenario
sets, snapshots outputs, and emits structured diffs suitable for release checks.

---

## Requirements

- [x] Add reusable golden-runner entrypoint for case set execution.
- [x] Emit machine-readable diff artifact per run/case.
- [x] Support baseline refresh flow with explicit operator intent.
- [x] Keep deterministic defaults for CI (mocked/synthetic where needed).

---

## Checklist

- [x] Runner docs include “check vs update” policy.
- [x] Diff output highlights semantic fields, not noisy raw blobs.
- [x] Makefile/CI integration path documented.

---

## Test / acceptance

- [x] Golden runner passes on unchanged baseline.
- [x] Intentional output change triggers diff and non-zero gate status.
- [x] Baseline update flow regenerates artifacts reproducibly.

Implemented artifacts:
- `apps/replay/golden_runner.py`
- `scripts/golden_runner.py`
- `scripts/golden_baseline.py` (check/update aligned with runner)
- `tests/test_golden_runner_ps45.py`
- `tests/fixtures/golden/replay_outcomes/` (deterministic replay fixtures)
- `docs/golden_run_baselines.md` (PS4.5 section)
- `Makefile` targets `golden-run`, `golden-check` (includes PS4.5 tests)
