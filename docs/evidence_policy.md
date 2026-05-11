# Evidence Policy (PS4.1)

This policy defines minimum grounding requirements for non-escalated agent outputs.

## Rules

1. Non-escalated runs must include at least one valid citation identifier (`doc_id` or `snippet_id`).
2. Any non-report plan step (for example `create_ticket`, `create_pr`, `change_config`) must reference grounding identifiers.
3. Plan step references must map to known identifiers from retrieved citations.
4. If grounding checks fail, the pipeline fails closed with escalation reason `evidence_policy_violation`.

## Rationale

- Prevent unsupported operational actions from being proposed as evidence-backed.
- Keep behavior deterministic and auditable under partial tool failures.
- Distinguish grounding violations from transport/tool outages (`tool_failure`) and pure no-data paths (`no_evidence`).

## Observability fields

Node spans include low-cardinality attributes:

- `evidence_policy_status`: `ok`, `violation`, or `skipped_escalated`
- `evidence_policy_reason`: short reason code when applicable

