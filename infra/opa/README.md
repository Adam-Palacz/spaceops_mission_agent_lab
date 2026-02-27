# OPA policy for restricted actions (S2.4)

This directory contains the OPA/Rego policy used by the agent's `Act` node to
decide whether a **restricted** plan step may proceed to approval (S2.4, NF8).

## Run OPA locally

- OPA runs as part of the local stack via `infra/docker-compose.yml`:

  ```bash
  docker compose -f infra/docker-compose.yml up -d opa
  ```

- The server listens on `http://localhost:8181` and loads policies from this
  directory (mounted at `/policies`).

## Policy entrypoint

- The agent calls `POST /v1/data/agent/allow` with:

  ```json
  {
    "input": {
      "incident_id": "inc-123",
      "step": {
        "action": "Restart ADCS service on sat-1",
        "action_type": "change_config",
        "safe": false,
        "doc_ids": ["..."],
        "snippet_ids": ["..."]
      }
    }
  }
  ```

- The policy in `agent_policy.rego` evaluates this input and returns:

  ```json
  { "result": true }
  ```

  when the action is allowed, or `false` when denied.

## Current rules (MVP)

- **Default deny (fail-closed):** `default allow = false`.
- **Allowlist:** only `action_type` values in `{"change_config", "restart_service"}`
  can ever be allowed.
- **Forbidden text:** if `step.action` contains `"restart all"` (case-insensitive),
  the request is denied.

S2.10 will add unit tests around these policies (allowlist, forbidden args, and
fail-closed behaviour) and may extend the rules (e.g. time-range validation).

