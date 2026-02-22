# Postmortem: Bus voltage below nominal — 2025-02

## Summary
During a routine pass, bus voltage dropped below nominal threshold (~27.5 V) for several samples. No load shed or safe-mode triggered. Event was triaged as Power subsystem, medium impact.

## Timeline (UTC)
- T+0: Ground reported "Bus voltage below nominal threshold" (event).
- T+1 min: Telemetry gap 2s on channel bus_voltage (ground log).
- T+2 min: Ops triggered anomaly review.

## Root cause
Post-analysis: temporary ground-station receiver glitch caused partial loss of telemetry; reconstructed data showed bus voltage within limits. Signature: event + gap in same pass, no sustained low on spacecraft side.

## Resolution
- Confirmed with flight dynamics and ground that no onboard action was required.
- Runbook *Power bus voltage anomaly* was updated with step to check for concurrent telemetry gap before escalating.
- Eval case added: event "Bus voltage below nominal" + ground log "Telemetry gap" → recommend "Confirm with ground; check for link glitch."

## Signature (for RAG/search)
Bus voltage below nominal, telemetry gap, Power subsystem, ground-station, link glitch, false positive.

## Tags
Power, telemetry gap, ground_logs, events, false positive.
