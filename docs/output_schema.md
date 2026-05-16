# Output Schema Policy (PS4.2)

Strict validation for primary agent output envelopes at pipeline boundaries and API responses.

## Envelopes

| Envelope | Model | Where enforced |
|----------|--------|----------------|
| Run report | `AgentReportV1` | `report` node, `POST /runs` response |
| Embedded escalation packet | `EmbeddedEscalationPacketV1` | `check_escalation`, `act`, `report` |
| Tool result row | `ToolResultV1` | `act`, `report` (`act_results`) |
| Approval request | `ApprovalRequestV1` | `act`, `report` (optional) |

Canonical definitions: `apps/contracts/v1.py`.  
Validation helpers: `apps/contracts/output_validation.py`.

The report is a single versioned wire/storage contract. `AgentRunReportEnvelope`
and related PS4.2 envelope names remain as compatibility aliases in
`apps/contracts/output_envelopes.py`.

## Fail-closed behavior

When validation fails inside the agent pipeline:

1. The run escalates with reason `output_schema_violation`.
2. A schema-safe escalation packet and report are emitted (no silent pass-through of malformed JSON).
3. Audit receives `guardrail_escalation` with `args.reason=output_schema_violation` and the failing `envelope`.

## API errors

If a report still fails validation at the API boundary, `POST /runs` (and simulate/resume paths) return **422** with a stable body:

```json
{
  "detail": {
    "error": "output_schema_violation",
    "envelope": "report",
    "message": "report: invalid field '...' (...)."
  }
}
```

## Observability

Node spans may include:

- `output_schema_status`: `ok` or `violation`
- `output_schema_reason`: `output_schema_violation` when applicable

## Verification

```bash
pytest tests/test_output_schema_ps42.py tests/test_guardrails_ps17.py tests/test_evidence_policy_ps41.py -v
```
