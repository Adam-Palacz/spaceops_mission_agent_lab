# PS4.3 — Prompt injection hardening pass

| Field | Value |
|-------|-------|
| **Task ID** | PS4.3 |
| **Status** | Done |

---

## Description

Harden agent prompt/input handling against injection patterns from telemetry, KB snippets, and
user-provided payloads. Preserve usability while prioritizing fail-closed safety.

---

## Requirements

- [x] Define injection threat patterns and blocked instruction classes.
- [x] Add sanitization/guard layer for untrusted text before prompt assembly.
- [x] Enforce allowlist for critical action intents and tool invocation signals.
- [x] Record injection-detection outcomes for audit and troubleshooting.

---

## Checklist

- [x] Threat-model note added to docs.
- [x] Sanitization path covered by unit tests.
- [x] Guard behavior integrated with escalation reasoning (not silent drop).

---

## Test / acceptance

- [x] Known injection fixture does not trigger unsafe action path.
- [x] Normal benign fixture still produces expected plan/report behavior.
- [x] Audit captures injection detection event with deterministic reason code.

Implemented artifacts:
- `apps/agent/prompt_injection.py`
- `apps/agent/nodes.py` (triage/decide/act guards + `check_escalation`)
- `apps/agent/state.py` (`injection_guard_*` fields)
- `evals/scoring.py` (shared allowlist with pipeline)
- `tests/test_prompt_injection_ps43.py`
- `docs/prompt_injection_threat_model.md`
