# PS1.1 — Data Contracts v1

| Field | Value |
|-------|--------|
| **Task ID** | PS1.1 |
| **Status** | Done |

---

## Description

Define and formalize v1 data contracts for core entities: `TelemetryEvent`, `Incident`,
`AgentReport`, and `EscalationPacket`. Contracts must be explicit, versioned, testable, and
exportable as JSON Schema so API, workers, evals, and replay rely on one source of truth.

---

## Requirements

- [x] Pydantic models exist for all four contracts in a stable module.
- [x] Each contract includes explicit version metadata (`schema_version` or equivalent).
- [x] JSON Schemas are exportable and committed under a predictable path.
- [x] Backward-compatibility rules are documented (what is additive vs breaking).
- [x] Unit tests validate model parsing and schema snapshots for v1.

---

## Checklist

- [x] Create contract module and model classes.
- [x] Add field-level descriptions and strict typing for required attributes.
- [x] Add schema export script/command.
- [x] Add docs section explaining versioning policy for contracts.
- [x] Add tests for valid and invalid payloads per contract.

---

## Test requirements

- [x] Contract tests pass for all valid v1 payloads.
- [x] Invalid payloads fail with clear validation errors.
- [x] Exported JSON Schemas are generated and stable in CI.
