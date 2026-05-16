# PS4.2 — Strict output schema checks for major envelopes

| Field | Value |
|-------|-------|
| **Task ID** | PS4.2 |
| **Status** | Done |

---

## Description

Apply strict schema validation to primary outputs (`report`, `escalation_packet`, tool result
envelopes) and ensure malformed outputs fail safely with diagnosable errors.

---

## Requirements

- [x] Define/confirm canonical schemas for report, escalation packet, and tool output envelopes.
- [x] Enforce validation at pipeline boundaries before persistence/response.
- [x] Add explicit error mapping for schema failures (operator-readable).
- [x] Keep backward-compatible handling for expected optional fields.

---

## Checklist

- [x] Validation is centralized (avoid duplicated ad-hoc checks).
- [x] Contract tests cover required and optional fields.
- [x] API responses for schema failures are stable and documented.

---

## Test / acceptance

- [x] Invalid report payload is rejected and does not silently pass.
- [x] Invalid escalation envelope fails closed with traceable reason.
- [x] Existing valid fixtures continue to pass after strict-mode rollout.

Implemented artifacts:
- `apps/contracts/v1.py` (unified `AgentReportV1`, `EmbeddedEscalationPacketV1`, tool/approval rows)
- `apps/contracts/output_envelopes.py` (compatibility aliases)
- `apps/contracts/output_validation.py`
- `contracts/schemas/v1/agent_report.schema.json` (regenerated)
- `apps/agent/nodes.py` (boundary enforcement + observability attrs)
- `apps/agent/graph.py` (run-timeout report validated)
- `apps/agent/state.py` (`output_schema_status` / `output_schema_reason`)
- `apps/api/main.py` (HTTP 422 stable `detail` on boundary failure)
- `tests/test_output_schema_ps42.py`
- `docs/output_schema.md`
