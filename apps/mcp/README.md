# MCP servers (`apps/mcp`)

Streamable HTTP MCP services used by the agent: **Telemetry**, **KB**, **Ticketing**, **GitOps**. Per-server notes live under each `*_server/` directory (for example `kb_server/README.md`).

## Transport security and `Host` (do not skip for production)

The Python MCP stack (`mcp.server.fastmcp.FastMCP`) defaults to `host="127.0.0.1"`. In that case it **auto-enables DNS rebinding protection**: only `Host` values like `127.0.0.1:*`, `localhost:*`, and `[::1]:*` are accepted. Any other host (for example **`telemetry-mcp:8001`** in Docker Compose) gets **HTTP 421** with body `Invalid Host header`.

**Lab / Docker Compose (current code):** each server passes `TransportSecuritySettings(enable_dns_rebinding_protection=False)` so internal service names work. That is appropriate on a **trusted private network**.

**If you expose an MCP endpoint on the public Internet:** do **not** leave rebinding protection disabled unless you fully understand the risk. Prefer:

- `enable_dns_rebinding_protection=True`, and  
- **`allowed_hosts`** (and **`allowed_origins`** if clients send `Origin`) listing the exact public hostnames and ports you serve (see `mcp.server.transport_security.TransportSecuritySettings` in the MCP package).

Alternatively keep the server bound to localhost behind a reverse proxy that terminates TLS and validates `Host`, and only route expected hostnames to the MCP upstream.

## Postgres in Docker Compose (KB server)

The KB MCP process uses `config.settings.postgres_dsn`. A host `.env` often sets `POSTGRES_HOST=localhost` or `DATABASE_URL=...@localhost...`, which is correct on the machine, but **wrong inside a container** (`localhost` is not the Postgres container).

`infra/docker-compose.yml` overrides **`DATABASE_URL`** for the **`kb-mcp`** service so it points at the Compose service **`postgres:5432`**, using the same `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` variables as the rest of the stack.

If your password contains characters that are special in URLs (`@`, `:`, `#`, `/`, etc.), you may need a percent-encoded password in that URL, or run KB MCP on the host with a hand-crafted `DATABASE_URL` instead of relying on this override.

### Keeping control of configuration (Compose + KB)

- **`kb-mcp` `DATABASE_URL` in Compose** only replaces the **hostname** with the Docker service `postgres`. User, password, and database name still come from the same `${POSTGRES_*}` variables you use for the `postgres` service (typically from `.env`). Nothing is hardcoded in the image; changing `.env` still drives auth.
- **Failures stay visible**: bad SQL, missing extension, or wrong types still surface as MCP/tool errors and OTel span errors (for example `error=true` on `mcp.kb.search_runbooks`) rather than being swallowed.
- **Prod / other orchestrators**: replicate the idea explicitly—inside the cluster use the stable DNS name of Postgres, not `localhost`, and manage secrets via your platform (K8s secrets, Vault, etc.) instead of relying on a developer `.env` meant for the laptop.
