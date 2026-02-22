# Runbook: Telemetry gap (missing or delayed samples)

## Scope
When ground logs or events report a telemetry gap (e.g. "Telemetry gap 2s on channel X").

## Prerequisites
- Ground logs and events for the pass.
- Telemetry data (to confirm which channels and time range).

## Steps

1. **Confirm**
   - Identify channel(s) and time range from ground logs.
   - Query telemetry for that range; confirm missing or duplicated timestamps.

2. **Classify**
   - Short gap (e.g. 1–2 s), single channel: often link or encoding; log and monitor.
   - Long or multiple channels: possible comms or onboard issue; escalate.

3. **Investigate**
   - Search postmortems for "telemetry gap" or "comms" to find past root causes.
   - Check runbooks for Comms and Payload for link health procedures.

4. **Decide**
   - Safe: create ticket, request pass summary from ground; add channel to watch list.
   - Restricted: none typically; escalation only if combined with other anomalies.

## References
- Comms runbook; Ground segment procedures.
- Postmortems: telemetry gap, Comms subsystem.
