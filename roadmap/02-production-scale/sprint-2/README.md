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

See **[BOARD.md](BOARD.md)** for status of PS2.1-PS2.8.

---

## Definition of done (sprint)

- [ ] Reviewer can diagnose scenario A/B using UI evidence + trace links only.
- [ ] Replay from stored inputs and fixture uploads is documented and executable.
- [ ] Golden-run diff workflow exists and is used in at least one CI check or manual gate.
- [ ] UI avoids non-operational features and keeps focus on decision support.
