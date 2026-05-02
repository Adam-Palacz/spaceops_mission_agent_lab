"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { API_BASE_URL } from "../../../lib/config";

export default function IncidentRunDetailPage() {
  const params = useParams();
  const runKey = decodeURIComponent(String(params.runKey || ""));
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runKey) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const resp = await fetch(
          `${API_BASE_URL}/runs/${encodeURIComponent(runKey)}`
        );
        const text = await resp.text();
        if (!resp.ok) {
          throw new Error(`${resp.status}: ${text}`);
        }
        const json = JSON.parse(text) as Record<string, unknown>;
        if (!cancelled) setData(json);
      } catch (e) {
        if (!cancelled) {
          setData(null);
          setError(e instanceof Error ? e.message : "Failed to load run");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [runKey]);

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: 24 }}>
      <p style={{ marginTop: 0 }}>
        <Link href="/incidents" style={{ color: "#9ecfff" }}>
          ← Incidents
        </Link>
      </p>
      <h1 style={{ marginBottom: 8 }}>Run: {runKey}</h1>
      <p style={{ color: "#a7b4c9", marginTop: 0 }}>
        PS2.2 will expand this view; for PS2.1 this is the linked detail with raw run JSON shape.
      </p>
      {loading ? <p>Loading…</p> : null}
      {error ? <p style={{ color: "#ff9090" }}>{error}</p> : null}
      {!loading && !error && data ? (
        <pre
          style={{
            background: "#111a2e",
            padding: 16,
            borderRadius: 8,
            overflow: "auto",
            fontSize: 12,
            border: "1px solid #243152",
          }}
        >
          {JSON.stringify(data, null, 2)}
        </pre>
      ) : null}
    </main>
  );
}
