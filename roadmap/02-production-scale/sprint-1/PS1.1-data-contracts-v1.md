# PS1.1 — Data Contracts v1

| Field | Value |
|-------|--------|
| **Task ID** | PS1.1 |
| **Status** | Todo |

---

## Description

Define and formalize v1 data contracts for core entities: `TelemetryEvent`, `Incident`,
`AgentReport`, and `EscalationPacket`. Contracts must be explicit, versioned, testable, and
exportable as JSON Schema so API, workers, evals, and replay rely on one source of truth.

---

## Requirements

- [ ] Pydantic models exist for all four contracts in a stable module.
- [ ] Each contract includes explicit version metadata (`schema_version` or equivalent).
- [ ] JSON Schemas are exportable and committed under a predictable path.
- [ ] Backward-compatibility rules are documented (what is additive vs breaking).
- [ ] Unit tests validate model parsing and schema snapshots for v1.

---

## Checklist

- [ ] Create contract module and model classes.
- [ ] Add field-level descriptions and strict typing for required attributes.
- [ ] Add schema export script/command.
- [ ] Add docs section explaining versioning policy for contracts.
- [ ] Add tests for valid and invalid payloads per contract.

---

## Test requirements

- [ ] Contract tests pass for all valid v1 payloads.
- [ ] Invalid payloads fail with clear validation errors.
- [ ] Exported JSON Schemas are generated and stable in CI.
