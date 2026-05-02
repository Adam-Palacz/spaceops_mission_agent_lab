export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const APPROVAL_API_KEY =
  process.env.NEXT_PUBLIC_APPROVAL_API_KEY || "";

/** Jaeger UI root (used when `trace_link` is absent but `trace_id` exists). */
export const JAEGER_UI_URL =
  process.env.NEXT_PUBLIC_JAEGER_UI_URL || "http://localhost:16686";

/** Subsystems aligned with agent triage (`apps/agent/nodes.py`). */
export const SUBSYSTEM_OPTIONS = [
  "",
  "ADCS",
  "Power",
  "Thermal",
  "Comms",
  "Payload",
  "Ground",
] as const;
