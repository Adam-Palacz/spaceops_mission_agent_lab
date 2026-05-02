# Distributed tracing verification (PS1.9)

This runbook verifies end-to-end trace continuity for Agent -> MCP calls and fail-path span status.

## What is implemented

- Agent outbound MCP calls inject W3C propagation headers (`traceparent`, `tracestate`).
- MCP services extract inbound W3C headers and continue the same trace.
- OPA evaluation and MCP execution paths use semantic spans with explicit `outcome`.
- Deny/failure paths set span status to `ERROR`.
- `report.trace_link` is emitted only for a valid 32-char trace id (no fake links when tracing is off).

## Local verification

1. Start stack (API + at least one MCP service + Jaeger/OTel collector).
2. Run a normal incident via API:
   - `POST /runs` with payload including time range/channels.
3. Open Jaeger trace from `report.trace_link`.
4. Confirm one trace includes spans from:
   - `agent.run` / `agent.decide` / `agent.act`
   - `mcp.client.*`
   - `mcp.telemetry.*` or other MCP service span.
5. Force deny/failure path (e.g. restricted step denied by OPA) and confirm:
   - span `policy.opa.evaluate` has `ERROR` status.

## Automated checks

- `pytest tests/test_ps19_tracing.py -v`
- `pytest tests/test_otel_jaeger.py -v`

## Security note

Only trace propagation headers are forwarded for context continuity.
No API keys, tokens, or credentials are attached as span attributes.

## Troubleshooting: Jaeger `trace not found` (404)

If `report.trace_link` opens Jaeger but returns **404**, the trace was **never stored** in that Jaeger instance.

Common cause when running **API/MCP in Docker**: `.env` sets `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`. Inside a container, `localhost` is the container itself, **not** the OTel collector, so spans are not exported.

**Fix:** `infra/docker-compose.yml` overrides this for `api` and all MCP services to `http://otel-collector:4317`. After changing compose, recreate containers:

```bash
docker compose -f infra/docker-compose.yml --project-directory . --profile ui up -d --build api telemetry-mcp kb-mcp ticket-mcp gitops-mcp
```

Then run a **new** incident and open the **new** `trace_link` (old IDs stay 404 if Jaeger was restarted or traces were never ingested).
