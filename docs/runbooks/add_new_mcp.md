# Runbook: How to add a new MCP

This runbook explains how to add a new MCP server to the SpaceOps Mission Agent Lab:
create the server, expose tools via the MCP protocol, register it in config, and wire
it into the agent where appropriate.

Use `apps/mcp/telemetry_server` and `apps/mcp/kb_server` as reference implementations.

---

## 1. Design the MCP: what tool(s) does it provide?

Before writing code, decide:

- **Purpose** — e.g. “Ticketing in another system”, “Change management system”, “Incident
  knowledge base in a different store”.
- **Tools** — each MCP exposes one or more tools; think in terms of:
  - function name (e.g. `create_ticket`, `query_slo`),
  - input arguments (JSON-serialisable),
  - returned JSON structure.

Keep tools **small and composable**; the agent’s prompts should describe *what* to do,
while MCP tools encode *how* to talk to the external system.

---

## 2. Create the MCP server skeleton

1. **Create a folder under `apps/mcp/`**:
   - Example: `apps/mcp/new_service_server/`.
2. **Add `main.py` entrypoint** modelled on existing servers:
   - Use the `mcp` Python package (see `apps/mcp/telemetry_server/main.py`).
   - Define one or more tools with type hints and docstrings.
   - Implement the handler logic (e.g. call an HTTP API, read from a DB, or from fixtures).
3. **Keep storage local by default**:
   - For MVP, prefer writing to `data/` (NDJSON or files) and reading from fixtures,
     mirroring what Telemetry/KB/Ticketing/GitOps do.

You should be able to run:

```bash
python -m apps.mcp.new_service_server.main
```

and see the MCP server start (usually on `http://localhost:<port>/mcp`).

---

## 3. Expose tools via MCP protocol

Within `main.py`:

- Register tools with the MCP framework, including:
  - tool name,
  - JSON schema for arguments (if applicable),
  - description.
- Make sure each tool:
  - validates inputs,
  - returns JSON-serialisable values,
  - handles errors gracefully (returning error objects rather than crashing).

The existing MCP servers show how to:

- read NDJSON/CSV/DB data,
- slice/filter by arguments,
- return structured results suitable for the agent (lists of dicts with `doc_id`,
  `content`, etc.).

---

## 4. Register the MCP in config

Add or reuse a URL setting in `config.py`:

- For example:

```python
new_service_mcp_url: str = Field(
    default="http://localhost:8005/mcp",
    description="MCP NewService (tool_name); used by agent for XYZ.",
)
```

- Add a matching variable to `.env.example` (commented), so operators know how to override
  the default URL.

This keeps the MCP endpoint configurable per environment.

---

## 5. Wire the MCP into the agent

Depending on what the MCP does, wire it into:

- **Investigate** (for read-only/context tools):
  - Add helper functions to `apps/agent/mcp_client.py` (async + sync wrappers),
    similar to `call_telemetry`, `call_search_runbooks`, etc.
  - Update `Investigate` in `apps/agent/nodes.py` to call the new MCP where it makes
    sense and translate results into `hypotheses` / `citations`.
- **Act** (for effectful tools):
  - Decide whether the tool is **safe** (no external risk) or **restricted** (requires
    OPA + approvals).
  - For safe tools, add a branch in `Act` that calls the new MCP when it sees the
    corresponding `action_type`.
  - For restricted tools, integrate it into OPA policy and approval flow, similar to
    existing `change_config` / `restart_service` behaviour.

Always:

- Audit tool calls via `apps.agent.audit_log.append_entry` with appropriate `tool` name,
- Consider whether the tool’s output should influence escalation or reporting.

---

## 6. Test and document

1. **Unit / integration tests**:
   - Add tests under `tests/` that:
     - exercise the MCP server (e.g. direct HTTP calls or MCP client),
     - exercise the agent path that uses the new MCP (Investigate/Act),
     - assert on audit log entries and error handling.
2. **Docs**:
   - Update `docs/architecture.md` or `docs/README.md` if the new MCP is a significant
     component.
   - Optionally add a short section in `docs/workflow/` diagrams if the pipeline changes.

---

## 7. Checklist

- [ ] New MCP server under `apps/mcp/<name>_server/` with `main.py`.
- [ ] Tools defined and exposed via MCP; server runs locally.
- [ ] Config entries (URL) added to `config.py` and `.env.example`.
- [ ] Agent wired to call the MCP where appropriate (Investigate and/or Act).
- [ ] Tests added to `tests/` covering both the MCP and agent integration.
- [ ] Docs/diagrams updated or linked so others can discover and understand the new MCP.

