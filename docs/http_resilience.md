# HTTP/MCP retry and circuit breaker (S3.4)

Shared layer for resilient HTTP and MCP calls: configurable retries with exponential backoff and an in-memory circuit breaker. Used by the OPA client and MCP client (Telemetry, KB, Ticketing, GitOps).

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `http_resilience_max_retries` | `3` | Maximum retry attempts for transient failures (0 = no retries). |
| `http_resilience_backoff_base_seconds` | `1.0` | Base delay for exponential backoff; jitter is applied. |
| `http_resilience_circuit_breaker_failures` | `5` | Number of failures before opening the circuit (0 = circuit breaker disabled). |
| `http_resilience_circuit_breaker_reset_seconds` | `60.0` | Seconds before the circuit moves from open to half-open (one trial). |

## Behaviour

- **Retryable**: `httpx.TimeoutException`, `httpx.ConnectError`, and HTTP 5xx / 429. Other errors are not retried.
- **Circuit breaker**: Per-key state (e.g. `opa`, `mcp_telemetry`). After N failures the circuit opens and further calls raise `CircuitOpenError` until the reset window has passed (then half-open, one attempt).
- **Fail-closed**: OPA and MCP callers catch `CircuitOpenError` and treat it as denial or empty result (no best-effort unsafe behaviour).

## API

- `with_retry_sync(fn, *args, circuit_key=None, **kwargs)` — sync calls (e.g. OPA).
- `with_retry_async(async_fn, *args, circuit_key=None, **kwargs)` — async calls (e.g. MCP).
- `CircuitOpenError(key)` — raised when the circuit is open for `key`.
- `reset_circuit(key=None)` — reset state for a key or all keys (for tests).

## Logging

Retries and circuit-open events are logged at INFO and WARNING so audit/monitoring can observe resilience behaviour.
