# PR2.2 - Secrets rotation and external secret proof

## Description

Prove that stage/prod secrets are not just designed but operable. Rotate secrets through the
approved external-secret path and verify workloads recover without leaking values.

## Requirements

- Use ESO/GSM/Vault or the selected stage/prod secret backend.
- Rotate OpenAI/LLM key, database password, approval token, MCP service token, and GitOps token
  where applicable.
- Validate rollout/restart behavior.
- Ensure logs, traces, audit events, and dashboards do not expose secret values.

## Checklist

- [ ] Secret inventory documented.
- [ ] Rotation procedure executed for at least the critical secret classes.
- [ ] Workload restart/rollout behavior verified.
- [ ] Leak check performed against logs/traces/audit.
- [ ] Rollback path documented.

## Test requirements

- Helm template check proves no plaintext stage/prod secrets are rendered.
- Manual or scripted rotation evidence.

