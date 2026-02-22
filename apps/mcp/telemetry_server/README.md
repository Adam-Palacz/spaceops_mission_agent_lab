# MCP Telemetry Server

Exposes **query_telemetry** over MCP (Streamable HTTP). Reads from `data/telemetry/*.ndjson` (fixtures and ingest output).

## Tool

- **query_telemetry(time_range_start, time_range_end, channels?)**
  - ISO8601 time range; optional list of channel names.
  - Returns list of telemetry records (ts, channel, value, subsystem, unit).

## Run

From repo root:

```bash
python -m apps.mcp.telemetry_server.main
```

Server: `http://0.0.0.0:8001/mcp` (MCP clients connect to this URL).

## Test

With MCP Inspector: `npx -y @modelcontextprotocol/inspector` → connect to `http://localhost:8001/mcp`, call `query_telemetry` with e.g. `time_range_start=2025-02-14T09:00:00Z`, `time_range_end=2025-02-14T11:00:00Z`.
