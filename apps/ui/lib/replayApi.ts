/**
 * PS2.6 — HTTP client for replay metadata + execute replay (`apps/api` PS1.4–PS1.5).
 * Outcome semantics match `apps/replay/workflow.compare_outcomes` / `scripts/replay_run.py`.
 */

import { API_BASE_URL } from "./config";

export type ReplayMetadataResponse = { replay: Record<string, unknown> };

export type ReplayComparison = {
  has_diff?: boolean;
  diffs?: Array<{ field: string; original: unknown; replay: unknown }>;
  original?: Record<string, unknown>;
  replay?: Record<string, unknown>;
};

export type ReplayRunResponse = {
  run_id: string;
  replay_run_id?: string;
  incident_id?: string;
  comparison?: ReplayComparison;
  metadata?: Record<string, unknown>;
};

export async function getReplayMetadata(
  runId: string,
): Promise<ReplayMetadataResponse> {
  const resp = await fetch(
    `${API_BASE_URL}/replays/${encodeURIComponent(runId.trim())}`,
  );
  const text = await resp.text();
  if (!resp.ok) {
    throw new Error(`${resp.status}: ${text}`);
  }
  return JSON.parse(text) as ReplayMetadataResponse;
}

export async function postReplayRun(runId: string): Promise<ReplayRunResponse> {
  const resp = await fetch(
    `${API_BASE_URL}/replays/${encodeURIComponent(runId.trim())}/run`,
    { method: "POST" },
  );
  const text = await resp.text();
  if (!resp.ok) {
    throw new Error(`${resp.status}: ${text}`);
  }
  return JSON.parse(text) as ReplayRunResponse;
}
