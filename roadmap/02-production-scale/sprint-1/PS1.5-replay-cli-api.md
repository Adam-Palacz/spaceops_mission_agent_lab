# PS1.5 — Replay CLI/API minimal workflow

| Field | Value |
|-------|--------|
| **Task ID** | PS1.5 |
| **Status** | Todo |

---

## Description

Provide a minimal replay interface (CLI and/or API) that re-runs a stored incident input and
compares key outputs (classification, escalation decision, evidence presence).

---

## Requirements

- [ ] Replay command/endpoint accepts `run_id` (or equivalent replay key).
- [ ] Replay executes pipeline with stored input metadata.
- [ ] Replay output includes comparison vs original run.
- [ ] Comparison highlights diffs in subsystem/escalation/citation presence.
- [ ] Replay path is documented for operators and developers.

---

## Checklist

- [ ] Implement replay entrypoint.
- [ ] Add comparison formatter (human-readable + machine-readable).
- [ ] Add guardrails for unsupported/missing replay metadata.
- [ ] Add docs examples for local and CI usage.
- [ ] Add tests for unchanged and changed behavior scenarios.

---

## Test requirements

- [ ] Replay of known run succeeds with deterministic core outcomes.
- [ ] Replay diff clearly shows regression when behavior changes.
- [ ] CLI/API return codes reflect success/failure conditions.
