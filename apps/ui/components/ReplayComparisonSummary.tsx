"use client";

import type { CSSProperties } from "react";
import type { ReplayComparison } from "../lib/replayApi";

export function ReplayComparisonSummary({ c }: { c: ReplayComparison }) {
  const hasDiff = Boolean(c.has_diff);
  return (
    <div>
      <p
        style={{
          fontWeight: 600,
          color: hasDiff ? "#f0c674" : "#8fd98f",
          marginTop: 0,
        }}
      >
        {hasDiff ? "Diff detected (core outcome changed)" : "No core outcome diff"}
      </p>
      <p style={{ fontSize: 13, color: "#a7b4c9", marginTop: 0 }}>
        Compared fields: <code>subsystem</code>, <code>escalated</code>,{" "}
        <code>has_citations</code> — same as <code>replay_by_run_id</code> / CLI exit{" "}
        <code>0</code> vs <code>2</code>.
      </p>
      {hasDiff && Array.isArray(c.diffs) && c.diffs.length > 0 ? (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #30405f" }}>
              <th style={th}>Field</th>
              <th style={th}>Baseline</th>
              <th style={th}>Replay</th>
            </tr>
          </thead>
          <tbody>
            {c.diffs.map((d, i) => (
              <tr key={`${d.field}-${i}`} style={{ borderBottom: "1px solid #1f2a40" }}>
                <td style={{ padding: "8px", fontFamily: "monospace" }}>{d.field}</td>
                <td style={{ padding: "8px" }}>{String(d.original)}</td>
                <td style={{ padding: "8px" }}>{String(d.replay)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}

const th: CSSProperties = { padding: "6px 8px" };
