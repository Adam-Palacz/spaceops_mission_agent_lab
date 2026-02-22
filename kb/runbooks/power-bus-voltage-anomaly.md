# Runbook: Power bus voltage anomaly

## Scope
When telemetry shows bus voltage below nominal (e.g. &lt; 28 V for a 28 V bus) or above safe margin, follow this runbook.

## Prerequisites
- Access to telemetry (MCP Telemetry or ingest data).
- Knowledge of nominal bus voltage and safe range for the mission.

## Steps

1. **Confirm the anomaly**
   - Query telemetry for `bus_voltage` (and related channels) over the reported time window.
   - Check ground logs for concurrent events (e.g. load shed, eclipse).

2. **Classify**
   - Transient (single sample): log and monitor; no action if within limits on next pass.
   - Sustained low: proceed to step 3.
   - Sustained high: see runbook *Power overvoltage*.

3. **Investigate**
   - Review power subsystem runbooks and postmortems for similar signatures.
   - Check for thermal or ADCS load spikes that could explain high demand.

4. **Decide**
   - Safe: create ticket, request ground review, add to next pass telemetry watch list.
   - Restricted: threshold change or load reconfiguration requires approval.

## References
- Mission power budget and nominal voltages (ops-config).
- Postmortem index for past bus voltage incidents.
