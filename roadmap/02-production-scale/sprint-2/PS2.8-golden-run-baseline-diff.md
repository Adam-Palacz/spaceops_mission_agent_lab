# PS2.8 — Golden-run baseline + diff (docs + workflow)

| Field | Value |
|-------|-------|
| **Task ID** | PS2.8 |
| **Status** | Todo |

---

## Description

Formalize **golden runs**: capture approved outputs for selected `run_id`s / eval cases, store **baseline
artifacts** (JSON or NDJSON under `data/replay/` or versioned `tests/fixtures/`), and define a **diff /
review checklist** for engineers before merge — aligned with PS1.5 replay machinery.

---

## Requirements

- [ ] Document baseline file layout, naming (`run_<id>_baseline.json` or similar), and update policy.
- [ ] Provide at least **one** scripted command or Makefile target: `golden:update` / `golden:check` (exact UX flexible).
- [ ] Integrate with **at least one CI check OR documented mandatory manual gate** before release (per sprint README DoD).
- [ ] Clarify what fields are compared (e.g. `subsystem`, `escalated`, `escalation_packet.reason`, citation counts).

---

## Checklist

- [ ] Link from `roadmap/02-production-scale/sprint-1` replay docs if present; avoid duplicating PS1.5 spec.
- [ ] Add short section to `docs/` or `evals/` README on when to refresh baselines after intentional model changes.

---

## Test / acceptance

- [ ] CI or script fails when baseline mismatch for pinned golden case (or checklist signed in PR template if CI deferred).
