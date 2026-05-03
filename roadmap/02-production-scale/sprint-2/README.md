# Production Scale — Sprint 2 (PS2)

**Goal:** deliver a thin operational UI and robust replay/golden-run workflows so reviewers can
diagnose incidents from evidence and compare behavior across revisions.

---

## Outcomes

- Incident-oriented UI flow (list/detail/evidence/timeline/escalation panel/trace link).
- Replay entry points from UI/CLI for deterministic reruns on known fixtures.
- Golden-run snapshots and baseline comparison integrated with engineering workflow.
- Documentation that enables external reviewer walkthrough without code deep-dive.

---

## Tasks

See **[BOARD.md](BOARD.md)** for status. Each task has a spec file `PS2.x-*.md` in this folder (same pattern as PS1).

---

## Definition of done (sprint)

- [ ] Reviewer can diagnose scenario A/B using UI evidence + trace links only.
- [ ] Replay from stored inputs and fixture uploads is documented and executable.
- [x] Golden-run diff workflow exists and is used in at least one CI check or manual gate (`pytest tests/test_golden_baseline.py`; see `docs/golden_run_baselines.md`).
- [ ] UI avoids non-operational features and keeps focus on decision support.

**Index:** cross-phase durability / safety / eval themes → [phase README — Cross-cutting](../README.md#cross-cutting-durability-safety-and-evals) (PS2.8 hands off to **PS4.5** golden runner depth).
