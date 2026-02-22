# Runbook: Thermal — plate temperature trending high

## Scope
When thermal telemetry shows plate (or panel) temperature trending above normal operating range.

## Prerequisites
- Telemetry channels: e.g. `temp_plate_1`, sun aspect, heater status.
- Events and ground logs for the same time range.

## Steps

1. **Confirm**
   - Query temperature channels over the reported window.
   - Correlate with sun exposure (eclipse vs daylight) and heater commands.

2. **Classify**
   - Within limits but trending up: increase monitoring; consider next pass thermal model update.
   - Above red limit: escalate; consider safe-mode or reduced power (see Power runbook).

3. **Investigate**
   - Search runbooks and postmortems for "thermal" and "temperature" to find similar cases.
   - Check for stuck heater or failed sensor (cross-check with other plates if available).

4. **Decide**
   - Safe: ticket, request thermal analysis, add to evals.
   - Restricted: heater or operational limit change requires approval.

## References
- Thermal model and limits in ops-config.
- Postmortems tagged with Thermal subsystem.
