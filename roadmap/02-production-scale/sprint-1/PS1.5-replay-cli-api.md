# PS1.5 — Replay CLI/API minimal workflow

| Field | Value |
|-------|--------|
| **Task ID** | PS1.5 |
| **Status** | Done |

---

## Description

Provide a minimal replay interface (CLI and/or API) that re-runs a stored incident input and
compares key outputs (classification, escalation decision, evidence presence).

---

## Requirements

- [x] Replay command/endpoint accepts `run_id` (or equivalent replay key).
- [x] Replay executes pipeline with stored input metadata.
- [x] Replay output includes comparison vs original run.
- [x] Comparison highlights diffs in subsystem/escalation/citation presence.
- [x] Replay path is documented for operators and developers.

---

## Checklist

- [x] Implement replay entrypoint.
- [x] Add comparison formatter (human-readable + machine-readable).
- [x] Add guardrails for unsupported/missing replay metadata.
- [x] Add docs examples for local and CI usage.
- [x] Add tests for unchanged and changed behavior scenarios.

---

## Test requirements

- [x] Replay of known run succeeds with deterministic core outcomes.
- [x] Replay diff clearly shows regression when behavior changes.
- [x] CLI/API return codes reflect success/failure conditions.
