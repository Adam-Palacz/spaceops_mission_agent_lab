# Chaos / degradation test harness (S3.5)

The harness simulates failures or slowdowns in key dependencies (MCP servers, OPA) and asserts that the agent **fails closed** or **escalates**—no hang, no unsafe action.

## Approach

We use **custom test fixtures** (no Toxiproxy or extra Docker services). Tests patch MCP/OPA call sites to simulate timeouts, 5xx, or unreachable services, then assert expected outcomes.

## Scenarios

| Scenario | What we simulate | Expected outcome |
|----------|------------------|------------------|
| **Telemetry MCP timeout** | `call_telemetry` raises `httpx.TimeoutException` | Investigate completes; fallback hypothesis "No telemetry or KB hits"; no exception. |
| **Telemetry MCP 5xx** | `call_telemetry` raises `httpx.HTTPStatusError` (500) | Same: investigate completes with empty telemetry and fallback hypothesis. |
| **KB MCP unavailable** | `call_search_runbooks` raises `httpx.ConnectError` | Investigate completes; fallback hypothesis; no hang. |
| **OPA unavailable / timeout** | `opa_allow` returns `False` (e.g. OPA down or circuit open) | Act escalates with `escalation_packet.reason == "policy_deny"`; no approval request; no execution. |

## How to run

Run all chaos/degradation tests:

```bash
pytest tests/test_chaos_degradation.py -v
```

Run a single scenario (example):

```bash
pytest tests/test_chaos_degradation.py::test_chaos_opa_unavailable_act_escalates_fail_closed -v
```

No extra setup: no Docker, no env vars (other than those required by the test suite, e.g. `AUDIT_LOG_PATH` in conftest). Cleanup is automatic (pytest isolation).

## Logs and audit

When MCP or OPA fails in real runs, the agent already:

- Logs tool outcome (`success` / `failure` / `empty`) and optional `error_message` in the audit log (S1.9).
- For OPA deny: logs `opa_check` with `outcome="failure"` and `error_message="OPA deny or unavailable"`.

So under degraded conditions, audit entries clearly indicate which dependency failed.

## Ensuring tests fail if behaviour regresses

- **OPA chaos**: If someone changes the Act node so that on OPA failure it creates an approval or executes the step, `test_chaos_opa_unavailable_act_escalates_fail_closed` and `test_chaos_opa_timeout_via_resilience_act_still_fails_closed` will fail (they assert `escalated is True`, `approval_requests == []`).
- **MCP chaos**: If investigate is changed to raise or hang when MCP fails, the investigate chaos tests will fail (they assert the node returns a state with the fallback hypothesis and no exception).
