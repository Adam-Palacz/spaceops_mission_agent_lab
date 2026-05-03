"use client";

import type { CSSProperties, ReactNode } from "react";
import Link from "next/link";
import { useCallback, useState } from "react";
import { ReplayComparisonSummary } from "../../components/ReplayComparisonSummary";
import { getReplayMetadata, postReplayRun, type ReplayRunResponse } from "../../lib/replayApi";

function Section({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section
      style={{
        marginBottom: 24,
        padding: 16,
        background: "#111a2e",
        borderRadius: 8,
        border: "1px solid #243152",
      }}
    >
      <h2 style={{ marginTop: 0, marginBottom: 12, fontSize: 18 }}>{title}</h2>
      {children}
    </section>
  );
}

export default function ReplaysPage() {
  const [runId, setRunId] = useState("");
  const [metaJson, setMetaJson] = useState<string | null>(null);
  const [replayResult, setReplayResult] = useState<ReplayRunResponse | null>(null);
  const [loadingMeta, setLoadingMeta] = useState(false);
  const [loadingReplay, setLoadingReplay] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onLoadMeta = useCallback(async () => {
    setError(null);
    setMetaJson(null);
    setReplayResult(null);
    const id = runId.trim();
    if (!id) {
      setError("Enter a run_id (UUID from a completed run JSON or replay file).");
      return;
    }
    setLoadingMeta(true);
    try {
      const data = await getReplayMetadata(id);
      setMetaJson(JSON.stringify(data.replay, null, 2));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load metadata");
    } finally {
      setLoadingMeta(false);
    }
  }, [runId]);

  const onRunReplay = useCallback(async () => {
    setError(null);
    setReplayResult(null);
    const id = runId.trim();
    if (!id) {
      setError("Enter a run_id first.");
      return;
    }
    setLoadingReplay(true);
    try {
      const out = await postReplayRun(id);
      setReplayResult(out);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Replay failed");
    } finally {
      setLoadingReplay(false);
    }
  }, [runId]);

  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: 24 }}>
      <p style={{ marginTop: 0 }}>
        <Link href="/incidents" style={{ color: "#9ecfff" }}>
          ← Incidents
        </Link>
      </p>
      <h1 style={{ marginBottom: 8 }}>Replay from stored run</h1>
      <p style={{ color: "#a7b4c9", marginTop: 0, fontSize: 14 }}>
        PS2.6 — uses <code>GET /replays/{"{run_id}"}</code> and{" "}
        <code>POST /replays/{"{run_id}"}/run</code> (same contract as{" "}
        <code>scripts/replay_run.py</code>). Use the pipeline <strong>run_id</strong> (UUID), not the
        incident run <strong>file</strong> name (<code>run_…json</code> stem).
      </p>

      <Section title="Run ID">
        <input
          type="text"
          value={runId}
          onChange={(e) => setRunId(e.target.value)}
          placeholder="e.g. abcdef0123456789… (32 hex from run detail)"
          spellCheck={false}
          style={inputStyle}
          autoComplete="off"
        />
        <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 8 }}>
          <button
            type="button"
            onClick={() => void onLoadMeta()}
            disabled={loadingMeta}
            style={btnPrimary}
          >
            {loadingMeta ? "Loading…" : "Load replay metadata"}
          </button>
          <button
            type="button"
            onClick={() => void onRunReplay()}
            disabled={loadingReplay}
            style={btnReplay}
          >
            {loadingReplay ? "Running replay…" : "Run replay & compare"}
          </button>
        </div>
        <p style={{ fontSize: 12, color: "#7a8aa6", marginBottom: 0 }}>
          Replay re-executes the full agent pipeline; allow time and ensure API can reach LLM/MCP
          like a normal <code>POST /runs</code>.
        </p>
      </Section>

      {error ? (
        <Section title="Error">
          <p style={{ color: "#ff9090", margin: 0, whiteSpace: "pre-wrap" }}>{error}</p>
        </Section>
      ) : null}

      {metaJson ? (
        <Section title="Replay metadata (read-only)">
          <pre
            style={{
              margin: 0,
              padding: 12,
              background: "#0b1220",
              borderRadius: 6,
              fontSize: 12,
              overflow: "auto",
              maxHeight: 280,
              border: "1px solid #243152",
            }}
          >
            {metaJson}
          </pre>
        </Section>
      ) : null}

      {replayResult ? (
        <Section title="Replay outcome">
          <p style={{ marginTop: 0 }}>
            <strong>Baseline run_id:</strong>{" "}
            <code style={{ fontSize: 13 }}>{replayResult.run_id}</code>
          </p>
          <p>
            <strong>New replay_run_id:</strong>{" "}
            <code style={{ fontSize: 13 }}>
              {replayResult.replay_run_id ? String(replayResult.replay_run_id) : "—"}
            </code>{" "}
            — new artifact under <code>data/incidents/</code>; find it at the top of{" "}
            <Link href="/incidents" style={{ color: "#9ecfff" }}>
              Incidents
            </Link>
            .
          </p>
          {replayResult.comparison ? (
            <ReplayComparisonSummary c={replayResult.comparison} />
          ) : null}
        </Section>
      ) : null}
    </main>
  );
}

const inputStyle: CSSProperties = {
  width: "100%",
  maxWidth: 520,
  boxSizing: "border-box",
  padding: "10px 12px",
  borderRadius: 6,
  border: "1px solid #30405f",
  background: "#0b1220",
  color: "#e7edf7",
  fontFamily: "monospace",
  fontSize: 14,
};

const btnPrimary: CSSProperties = {
  padding: "10px 16px",
  borderRadius: 6,
  border: "none",
  background: "#2a6fdb",
  color: "#fff",
  cursor: "pointer",
  fontWeight: 600,
};

const btnReplay: CSSProperties = {
  ...btnPrimary,
  background: "#6b4f9e",
};
