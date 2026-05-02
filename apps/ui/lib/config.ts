export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const APPROVAL_API_KEY =
  process.env.NEXT_PUBLIC_APPROVAL_API_KEY || "";

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
