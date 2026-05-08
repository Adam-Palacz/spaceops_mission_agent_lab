# PS4.5 — Golden runner snapshot/diff

| Field | Value |
|-------|-------|
| **Task ID** | PS4.5 |
| **Status** | Todo |

---

## Description

Deepen golden-run workflows from PS2.8 into a repeatable runner that executes selected scenario
sets, snapshots outputs, and emits structured diffs suitable for release checks.

---

## Requirements

- [ ] Add reusable golden-runner entrypoint for case set execution.
- [ ] Emit machine-readable diff artifact per run/case.
- [ ] Support baseline refresh flow with explicit operator intent.
- [ ] Keep deterministic defaults for CI (mocked/synthetic where needed).

---

## Checklist

- [ ] Runner docs include “check vs update” policy.
- [ ] Diff output highlights semantic fields, not noisy raw blobs.
- [ ] Makefile/CI integration path documented.

---

## Test / acceptance

- [ ] Golden runner passes on unchanged baseline.
- [ ] Intentional output change triggers diff and non-zero gate status.
- [ ] Baseline update flow regenerates artifacts reproducibly.
