# PS4.2 — Strict output schema checks for major envelopes

| Field | Value |
|-------|-------|
| **Task ID** | PS4.2 |
| **Status** | Todo |

---

## Description

Apply strict schema validation to primary outputs (`report`, `escalation_packet`, tool result
envelopes) and ensure malformed outputs fail safely with diagnosable errors.

---

## Requirements

- [ ] Define/confirm canonical schemas for report, escalation packet, and tool output envelopes.
- [ ] Enforce validation at pipeline boundaries before persistence/response.
- [ ] Add explicit error mapping for schema failures (operator-readable).
- [ ] Keep backward-compatible handling for expected optional fields.

---

## Checklist

- [ ] Validation is centralized (avoid duplicated ad-hoc checks).
- [ ] Contract tests cover required and optional fields.
- [ ] API responses for schema failures are stable and documented.

---

## Test / acceptance

- [ ] Invalid report payload is rejected and does not silently pass.
- [ ] Invalid escalation envelope fails closed with traceable reason.
- [ ] Existing valid fixtures continue to pass after strict-mode rollout.
