"use client";

import type { CSSProperties, FormEvent } from "react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { API_BASE_URL, JAEGER_UI_URL, SUBSYSTEM_OPTIONS } from "../../lib/config";
import { buildJaegerTraceHref } from "../../lib/jaegerTrace";

export type RunListItem = {
  id: string;
  run_id: string;
  incident_id: string;
  status: "completed" | "error";
  created_at: string;
  summary?: string | null;
  error?: string | null;
  subsystem?: string;
  risk?: string;
  escalated?: boolean;
  sat_id?: string;
  confidence?: string;
  /** 32-char hex when OTel trace was recorded (PS2.5). */
  trace_id?: string | null;
  /** Absolute URL from report when agent emitted `trace_link` (PS2.5). */
  trace_link?: string | null;
};

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  if (!resp.ok) {
    const message = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${message}`);
  }
  return (await resp.json()) as T;
}

function buildQuery(sp: URLSearchParams): string {
  const q = new URLSearchParams();
  const lim = sp.get("limit") || "50";
  if (lim) q.set("limit", lim);
  const keys = [
    "subsystem",
    "risk",
    "status",
    "sat_id",
    "confidence",
    "after",
    "before",
  ] as const;
  for (const k of keys) {
    const v = sp.get(k);
    if (v) q.set(k, v);
  }
  const esc = sp.get("escalated");
  if (esc === "true" || esc === "false") q.set("escalated", esc);
  return q.toString();
}

export default function IncidentsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const qs = buildQuery(searchParams);
      const data = await fetchJson<{ runs: RunListItem[] }>(
        `${API_BASE_URL}/runs${qs ? `?${qs}` : ""}`
      );
      setRuns(data.runs || []);
    } catch (err) {
      setRuns([]);
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [searchParams]);

  useEffect(() => {
    void load();
  }, [load]);

  const formDefaults = useMemo(() => {
    const sp = searchParams;
    return {
      subsystem: sp.get("subsystem") || "",
      risk: sp.get("risk") || "",
      status: sp.get("status") || "",
      escalated: sp.get("escalated") || "",
      confidence: sp.get("confidence") || "",
      sat_id: sp.get("sat_id") || "",
      after: sp.get("after") || "",
      before: sp.get("before") || "",
    };
  }, [searchParams]);

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const next = new URLSearchParams();
    next.set("limit", "50");
    const copy = [
      "subsystem",
      "risk",
      "status",
      "escalated",
      "confidence",
      "sat_id",
      "after",
      "before",
    ] as const;
    for (const k of copy) {
      const v = (fd.get(k) as string)?.trim();
      if (v) next.set(k, v);
    }
    router.push(`${pathname}?${next.toString()}`);
  };

  const onClear = () => {
    router.push(pathname);
  };

  return (
    <main style={{ maxWidth: 1200, margin: "0 auto", padding: 24 }}>
      <h1 style={{ marginBottom: 8 }}>Incidents / runs</h1>
      <p style={{ marginTop: 0, color: "#a7b4c9" }}>
        API: <code>{API_BASE_URL}</code> — filters use <code>GET /runs</code> query params (PS2.1).
        Jaeger deep links use <code>NEXT_PUBLIC_JAEGER_UI_URL</code> ({JAEGER_UI_URL}) when{" "}
        <code>trace_link</code> is absent (PS2.5).
      </p>

      <form
        onSubmit={onSubmit}
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
          gap: 12,
          marginBottom: 20,
          padding: 16,
          background: "#111a2e",
          borderRadius: 8,
          border: "1px solid #243152",
        }}
      >
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span>Subsystem</span>
          <select
            name="subsystem"
            defaultValue={formDefaults.subsystem}
            style={inputStyle}
          >
            {SUBSYSTEM_OPTIONS.map((s) => (
              <option key={s || "any"} value={s}>
                {s || "(any)"}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span>Risk</span>
          <select name="risk" defaultValue={formDefaults.risk} style={inputStyle}>
            <option value="">(any)</option>
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span>Run status</span>
          <select name="status" defaultValue={formDefaults.status} style={inputStyle}>
            <option value="">(any)</option>
            <option value="completed">completed</option>
            <option value="error">error</option>
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span>Escalated</span>
          <select
            name="escalated"
            defaultValue={formDefaults.escalated}
            style={inputStyle}
          >
            <option value="">(any)</option>
            <option value="true">yes</option>
            <option value="false">no</option>
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span>Confidence</span>
          <select
            name="confidence"
            defaultValue={formDefaults.confidence}
            style={inputStyle}
          >
            <option value="">(any)</option>
            <option value="high">high</option>
            <option value="medium">medium</option>
            <option value="low">low</option>
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span>Sat / payload id</span>
          <input
            name="sat_id"
            type="text"
            placeholder="substring…"
            defaultValue={formDefaults.sat_id}
            style={inputStyle}
            autoComplete="off"
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span>After (ISO)</span>
          <input
            name="after"
            type="text"
            placeholder="2026-05-01T00:00:00Z"
            defaultValue={formDefaults.after}
            style={inputStyle}
            autoComplete="off"
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span>Before (ISO)</span>
          <input
            name="before"
            type="text"
            placeholder="2026-05-31T23:59:59Z"
            defaultValue={formDefaults.before}
            style={inputStyle}
            autoComplete="off"
          />
        </label>
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            gap: 8,
            gridColumn: "1 / -1",
          }}
        >
          <button type="submit" style={btnPrimary}>
            Apply filters
          </button>
          <button type="button" onClick={onClear} style={btnGhost}>
            Clear
          </button>
        </div>
      </form>

      {loading ? <p>Loading…</p> : null}
      {error ? <p style={{ color: "#ff9090" }}>{error}</p> : null}
      {!loading && !error && runs.length === 0 ? <p>No runs match.</p> : null}
      {!loading && !error && runs.length > 0 ? (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #30405f" }}>
              <th style={th}>Incident</th>
              <th style={th}>Subsystem</th>
              <th style={th}>Risk</th>
              <th style={th}>Esc.</th>
              <th style={th}>Conf.</th>
              <th style={th}>Status</th>
              <th style={th}>Summary / error</th>
              <th style={th}>Jaeger</th>
              <th style={th}>Created (UTC)</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => {
              const jaegerHref = buildJaegerTraceHref({
                jaegerUiRoot: JAEGER_UI_URL,
                traceLink: run.trace_link,
                traceId: run.trace_id,
              });
              return (
              <tr key={run.id} style={{ borderBottom: "1px solid #1f2a40" }}>
                <td style={td}>
                  <Link
                    href={`/incidents/${encodeURIComponent(run.id)}`}
                    style={{ color: "#9ecfff" }}
                  >
                    {run.incident_id || "—"}
                  </Link>
                </td>
                <td style={td}>{run.subsystem || "—"}</td>
                <td style={td}>{run.risk || "—"}</td>
                <td style={td}>{run.escalated ? "yes" : "no"}</td>
                <td style={td}>{run.confidence || "—"}</td>
                <td style={td}>{run.status}</td>
                <td style={td}>
                  {(run.summary || run.error || "—").slice(0, 120)}
                  {(run.summary || run.error || "").length > 120 ? "…" : ""}
                </td>
                <td style={td}>
                  {jaegerHref ? (
                    <a
                      href={jaegerHref}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="Open trace in Jaeger (new tab)"
                      style={{ color: "#9ecfff", fontSize: 13, whiteSpace: "nowrap" }}
                    >
                      View trace ↗
                    </a>
                  ) : (
                    <span
                      style={{ color: "#7a8aa6", fontSize: 12 }}
                      title="No trace_id / trace_link for this run (pre-OTel or export misconfigured)"
                    >
                      —
                    </span>
                  )}
                </td>
                <td style={tdMono}>{run.created_at}</td>
              </tr>
            );
            })}
          </tbody>
        </table>
      ) : null}
    </main>
  );
}

const inputStyle: CSSProperties = {
  padding: "8px 10px",
  borderRadius: 6,
  border: "1px solid #30405f",
  background: "#0b1220",
  color: "#e7edf7",
};

const btnPrimary: CSSProperties = {
  padding: "10px 18px",
  borderRadius: 6,
  border: "none",
  background: "#2a6fdb",
  color: "#fff",
  cursor: "pointer",
  fontWeight: 600,
};

const btnGhost: CSSProperties = {
  padding: "10px 18px",
  borderRadius: 6,
  border: "1px solid #30405f",
  background: "transparent",
  color: "#e7edf7",
  cursor: "pointer",
};

const th: CSSProperties = { padding: "8px 8px", fontSize: 13 };
const td: CSSProperties = { padding: "10px 8px", verticalAlign: "top" };
const tdMono: CSSProperties = { ...td, fontSize: 12, whiteSpace: "nowrap" };
