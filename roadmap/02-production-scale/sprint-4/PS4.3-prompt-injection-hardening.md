# PS4.3 — Prompt injection hardening pass

| Field | Value |
|-------|-------|
| **Task ID** | PS4.3 |
| **Status** | Todo |

---

## Description

Harden agent prompt/input handling against injection patterns from telemetry, KB snippets, and
user-provided payloads. Preserve usability while prioritizing fail-closed safety.

---

## Requirements

- [ ] Define injection threat patterns and blocked instruction classes.
- [ ] Add sanitization/guard layer for untrusted text before prompt assembly.
- [ ] Enforce allowlist for critical action intents and tool invocation signals.
- [ ] Record injection-detection outcomes for audit and troubleshooting.

---

## Checklist

- [ ] Threat-model note added to docs.
- [ ] Sanitization path covered by unit tests.
- [ ] Guard behavior integrated with escalation reasoning (not silent drop).

---

## Test / acceptance

- [ ] Known injection fixture does not trigger unsafe action path.
- [ ] Normal benign fixture still produces expected plan/report behavior.
- [ ] Audit captures injection detection event with deterministic reason code.
