# Contracts

Canonical JSON Schemas for versioned data contracts used across API, agent runs, replay,
and evals.

Current version:

- `schemas/v1/telemetry_event.schema.json`
- `schemas/v1/incident.schema.json`
- `schemas/v1/agent_report.schema.json`
- `schemas/v1/escalation_packet.schema.json`

Runtime pipeline output models (report / embedded escalation / tool results) are defined in
`apps/contracts/v1.py`; see [docs/output_schema.md](../docs/output_schema.md).

Regenerate schemas:

```bash
python scripts/export_contract_schemas.py
```

Compatibility policy (v1):

- Additive changes (new optional fields) are backward compatible.
- Tightening existing field constraints or removing/renaming fields is breaking.
- Breaking changes require a new contract version directory (`schemas/v2/`) and migration notes.
