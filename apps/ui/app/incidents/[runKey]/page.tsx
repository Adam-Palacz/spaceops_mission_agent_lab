"use client";

import type { CSSProperties, ReactNode } from "react";
import { Fragment } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ReplayComparisonSummary } from "../../../components/ReplayComparisonSummary";
import { API_BASE_URL, JAEGER_UI_URL } from "../../../lib/config";
import { buildJaegerTraceHref } from "../../../lib/jaegerTrace";
import { postReplayRun, type ReplayRunResponse } from "../../../lib/replayApi";

type Json = Record<string, unknown>;

function isRecord(v: unknown): v is Json {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function asStr(v: unknown): string {
  if (typeof v === "string") return v;
  if (v === null || v === undefined) return "";
  return String(v);
}

function ExpandableText({
  text,
  maxChars = 280,
}: {
  text: string;
  maxChars?: number;
}) {
  const [open, setOpen] = useState(false);
  if (!text) return <span style={{ color: "#7a8aa6" }}>—</span>;
  const need = text.length > maxChars;
  const shown = open || !need ? text : `${text.slice(0, maxChars)}…`;
  return (
    <span>
      {shown}
      {need ? (
        <button
          type="button"
          onClick={() => setOpen(!open)}
          style={{
            marginLeft: 8,
            border: "none",
            background: "transparent",
            color: "#9ecfff",
            cursor: "pointer",
            textDecoration: "underline",
            fontSize: "inherit",
          }}
        >
          {open ? "Show less" : "Show more"}
        </button>
      ) : null}
    </span>
  );
}

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

function formatStageDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return "0 ms";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

/** PS2.4 — EscalationPacket fields align with `apps/agent/state.EscalationPacket` / contracts v1. */
const ESCALATION_LIST_SECTIONS = [
  { key: "what_we_know", title: "What we know" },
  { key: "what_we_dont_know", title: "What we don't know" },
  { key: "what_to_check", title: "What to check next" },
] as const;

function mergeEscalationPacket(data: Json | null, report: Json | null): Json | null {
  const fromReport =
    report && isRecord(report.escalation_packet) ? report.escalation_packet : null;
  const fromRoot =
    data && isRecord(data.escalation_packet) ? data.escalation_packet : null;
  const pick = fromReport ?? fromRoot;
  return pick && isRecord(pick) ? pick : null;
}

function stringListFromField(packet: Json, field: string): string[] {
  const raw = packet[field];
  if (!Array.isArray(raw)) return [];
  return raw.map((x) => asStr(x).trim()).filter(Boolean);
}

function escalationPacketHasDisplayableContent(packet: Json | null): boolean {
  if (!packet || Object.keys(packet).length === 0) return false;
  if (asStr(packet.reason).trim()) return true;
  for (const { key } of ESCALATION_LIST_SECTIONS) {
    if (stringListFromField(packet, key).length > 0) return true;
  }
  return false;
}

function reportLooksEscalated(report: Json | null): boolean {
  if (!report) return false;
  const es = asStr(report.executive_summary) || asStr(report.summary);
  return es.startsWith("[ESCALATION]");
}

function shouldShowEscalationPanel(
  data: Json,
  report: Json | null,
  packet: Json | null,
): boolean {
  if (data.escalated === true) return true;
  if (reportLooksEscalated(report)) return true;
  return escalationPacketHasDisplayableContent(packet);
}

export default function IncidentRunDetailPage() {
  const params = useParams();
  const runKey = decodeURIComponent(String(params.runKey || ""));
  const [data, setData] = useState<Json | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRaw, setShowRaw] = useState(false);
  const [replayLoading, setReplayLoading] = useState(false);
  const [replayErr, setReplayErr] = useState<string | null>(null);
  const [replayOut, setReplayOut] = useState<ReplayRunResponse | null>(null);

  useEffect(() => {
    setReplayErr(null);
    setReplayOut(null);
  }, [runKey]);

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
        const json = JSON.parse(text) as Json;
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

  const report = useMemo(() => {
    if (!data) return null;
    const r = data.report;
    return isRecord(r) ? r : null;
  }, [data]);

  const traceUrl = useMemo(
    () =>
      data
        ? buildJaegerTraceHref({
            jaegerUiRoot: JAEGER_UI_URL,
            traceLink: report ? asStr(report.trace_link) : "",
            traceId: asStr(data.trace_id),
          })
        : null,
    [data, report],
  );

  const stageTimings = useMemo(() => {
    if (!data) return [];
    const st = data.stage_timings;
    if (!Array.isArray(st)) return [];
    const out: { node: string; duration_ms: number; status: string }[] = [];
    for (const row of st) {
      if (!isRecord(row)) continue;
      const node = asStr(row.node);
      if (!node) continue;
      const dm = row.duration_ms;
      const duration_ms =
        typeof dm === "number" && Number.isFinite(dm) ? Math.max(0, dm) : 0;
      const status = asStr(row.status) || "ok";
      out.push({ node, duration_ms, status });
    }
    return out;
  }, [data]);

  const timelineTotalMs = useMemo(
    () => stageTimings.reduce((acc, r) => acc + r.duration_ms, 0),
    [stageTimings]
  );

  const pipelineRunId = useMemo(
    () => (data ? asStr(data.run_id).trim() : ""),
    [data],
  );

  const evidenceItems = useMemo(() => {
    if (!report) return [];
    const ev = report.evidence;
    if (!Array.isArray(ev)) return [];
    return ev.filter((x) => isRecord(x) || typeof x === "string");
  }, [report]);

  const citationRefs = useMemo(() => {
    if (!report) return [];
    const cr = report.citation_refs;
    if (!Array.isArray(cr)) return [];
    return cr.map((x) => asStr(x)).filter(Boolean);
  }, [report]);

  const structuredCitations = useMemo(() => {
    if (!data) return [];
    const c = data.citations;
    if (!Array.isArray(c)) return [];
    return c.filter(isRecord);
  }, [data]);

  const actResults = useMemo(() => {
    if (!report) return [];
    const ar = report.act_results;
    if (!Array.isArray(ar)) return [];
    return ar.filter(isRecord);
  }, [report]);

  const approvalRequests = useMemo(() => {
    if (!report) return [];
    const ar = report.approval_requests;
    if (!Array.isArray(ar)) return [];
    return ar.filter(isRecord);
  }, [report]);

  const proposedActions = useMemo(() => {
    if (!report) return [];
    const pa = report.proposed_actions;
    if (!Array.isArray(pa)) return [];
    return pa.map((x) => asStr(x)).filter(Boolean);
  }, [report]);

  const escalationPacket = useMemo(
    () => mergeEscalationPacket(data, report),
    [data, report],
  );

  const showEscalationPanel = useMemo(
    () =>
      data ? shouldShowEscalationPanel(data, report, escalationPacket) : false,
    [data, report, escalationPacket],
  );

  const escalationTagReason = useMemo(() => {
    if (!report) return "";
    const t = report.escalation_reason;
    return typeof t === "string" ? t.trim() : "";
  }, [report]);

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: 24 }}>
      <p style={{ marginTop: 0 }}>
        <Link href="/incidents" style={{ color: "#9ecfff" }}>
          ← Incidents
        </Link>
      </p>
      <h1 style={{ marginBottom: 4 }}>Incident detail</h1>
      <p style={{ color: "#a7b4c9", marginTop: 0, fontSize: 14 }}>
        Run file: <code>{runKey}</code>
      </p>

      {!loading && !error && data && data.simulation === true ? (
        <div
          style={{
            padding: 12,
            marginBottom: 16,
            background: "#2a2410",
            border: "1px solid #c9a227",
            borderRadius: 8,
          }}
        >
          <strong style={{ color: "#f0e6cc" }}>Fixture simulation (PS2.7)</strong>
          <p style={{ margin: "8px 0 0", fontSize: 13, color: "#e8d89a" }}>
            Pipeline ran under synthetic <code>sim-upload-…</code> id. Declared incident in fixture:{" "}
            <code>{asStr(data.source_fixture_incident_id) || "—"}</code>
            {asStr(data.fixture_upload_name) ? (
              <>
                {" "}
                · file <code>{asStr(data.fixture_upload_name)}</code>
              </>
            ) : null}
          </p>
        </div>
      ) : null}

      {loading ? <p>Loading…</p> : null}
      {error ? <p style={{ color: "#ff9090" }}>{error}</p> : null}

      {!loading && !error && data ? (
        <>
          <Section title="Run metadata">
            <dl style={dlStyle}>
              <dt>Incident ID</dt>
              <dd>{asStr(data.incident_id) || "—"}</dd>
              <dt>Run ID</dt>
              <dd>{asStr(data.run_id) || "—"}</dd>
              <dt>Subsystem</dt>
              <dd>{asStr(data.subsystem) || "—"}</dd>
              <dt>Risk</dt>
              <dd>{asStr(data.risk) || "—"}</dd>
              <dt>Escalated</dt>
              <dd>{data.escalated === true ? "yes" : data.escalated === false ? "no" : "—"}</dd>
              <dt>Trace ID</dt>
              <dd style={{ wordBreak: "break-all", fontFamily: "monospace", fontSize: 13 }}>
                {asStr(data.trace_id) || "—"}
              </dd>
            </dl>
          </Section>

          {asStr(data.error) ? (
            <Section title="Pipeline error">
              <p style={{ color: "#ff9090", whiteSpace: "pre-wrap" }}>
                <ExpandableText text={asStr(data.error)} maxChars={400} />
              </p>
            </Section>
          ) : null}

          {report ? (
            <Section title="Summary / report">
              <p style={{ lineHeight: 1.5, marginTop: 0 }}>
                <ExpandableText
                  text={
                    asStr(report.executive_summary) ||
                    asStr(report.summary) ||
                    "No executive summary."
                  }
                  maxChars={400}
                />
              </p>
              {asStr(report.rollback) ? (
                <p style={{ fontSize: 13, color: "#a7b4c9", marginBottom: 0 }}>
                  <strong>Rollback:</strong>{" "}
                  <ExpandableText text={asStr(report.rollback)} maxChars={200} />
                </p>
              ) : null}
            </Section>
          ) : !asStr(data.error) ? (
            <Section title="Summary / report">
              <p style={{ color: "#7a8aa6" }}>No report object in this run file.</p>
            </Section>
          ) : null}

          {showEscalationPanel ? (
            <Section title="Escalation packet (human handoff)">
              <div
                style={{
                  borderLeft: "4px solid #c9a227",
                  paddingLeft: 14,
                  marginTop: 0,
                }}
              >
                <p style={{ fontSize: 13, color: "#e8d89a", marginTop: 0 }}>
                  Structured handoff fields (<code style={{ fontSize: 12 }}>EscalationPacket</code>
                  ). Absent bullets mean the agent left no lines for that bucket — not “skipped stages”.
                </p>
                {(data.escalated === true || reportLooksEscalated(report)) &&
                (!escalationPacket || Object.keys(escalationPacket).length === 0 ||
                  !escalationPacketHasDisplayableContent(escalationPacket)) ? (
                  <p style={{ fontSize: 13, color: "#a7b4c9", marginBottom: 12 }}>
                    No structured <code>escalation_packet</code> in this run file — use summary,
                    run metadata, and trace below (legacy or incomplete persist).
                  </p>
                ) : null}
                <p style={{ marginTop: 0, marginBottom: 12 }}>
                  <strong style={{ color: "#f0e6cc" }}>Reason</strong>{" "}
                  <span>
                    {escalationPacket && asStr(escalationPacket.reason).trim()
                      ? asStr(escalationPacket.reason)
                      : "—"}
                  </span>
                </p>
                {escalationTagReason &&
                escalationTagReason !==
                  (escalationPacket ? asStr(escalationPacket.reason).trim() : "") ? (
                  <p style={{ fontSize: 12, color: "#a7b4c9", marginTop: -8, marginBottom: 12 }}>
                    Tracing tag <code>escalation_reason</code>:{" "}
                    <code style={{ color: "#9ecfff" }}>{escalationTagReason}</code>
                  </p>
                ) : null}
                {ESCALATION_LIST_SECTIONS.map(({ key, title }) => {
                  const items = escalationPacket
                    ? stringListFromField(escalationPacket, key)
                    : [];
                  return (
                    <div key={key} style={{ marginBottom: 14 }}>
                      <h3 style={escalationSubheadingStyle}>{title}</h3>
                      {items.length === 0 ? (
                        <p
                          style={{
                            color: "#7a8aa6",
                            margin: "4px 0 0",
                            fontSize: 13,
                          }}
                        >
                          (none)
                        </p>
                      ) : (
                        <ul style={{ margin: "4px 0 0", paddingLeft: 20 }}>
                          {items.map((text, i) => (
                            <li key={i} style={{ marginBottom: 6 }}>
                              <ExpandableText text={text} maxChars={280} />
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  );
                })}
              </div>
            </Section>
          ) : null}

          {report && proposedActions.length > 0 ? (
            <Section title="Proposed actions (plan text)">
              <ol style={{ margin: 0, paddingLeft: 20 }}>
                {proposedActions.map((a, i) => (
                  <li key={i} style={{ marginBottom: 8 }}>
                    <ExpandableText text={a} maxChars={220} />
                  </li>
                ))}
              </ol>
            </Section>
          ) : null}

          <Section title="Evidence">
            {evidenceItems.length === 0 &&
            citationRefs.length === 0 &&
            structuredCitations.length === 0 ? (
              <p style={{ color: "#7a8aa6", margin: 0 }}>No structured evidence in this run.</p>
            ) : null}
            {evidenceItems.length > 0 ? (
              <>
                <h3 style={h3Style}>Investigation notes</h3>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {evidenceItems.map((item, i) => (
                    <li key={i} style={{ marginBottom: 10 }}>
                      {typeof item === "string" ? (
                        <ExpandableText text={item} maxChars={240} />
                      ) : (
                        <ExpandableText
                          text={
                            asStr(item.hypothesis) ||
                            asStr(item.content) ||
                            JSON.stringify(item)
                          }
                          maxChars={240}
                        />
                      )}
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
            {citationRefs.length > 0 ? (
              <>
                <h3 style={h3Style}>Citation refs</h3>
                <ul style={{ display: "flex", flexWrap: "wrap", gap: 8, listStyle: "none", padding: 0, margin: 0 }}>
                  {citationRefs.map((ref) => (
                    <li
                      key={ref}
                      style={{
                        background: "#1a2744",
                        padding: "4px 10px",
                        borderRadius: 6,
                        fontSize: 13,
                        border: "1px solid #30405f",
                      }}
                    >
                      {ref}
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
            {structuredCitations.length > 0 ? (
              <>
                <h3 style={h3Style}>Citations (structured)</h3>
                <ul style={{ margin: 0, paddingLeft: 0, listStyle: "none" }}>
                  {structuredCitations.map((c, i) => (
                    <li
                      key={i}
                      style={{
                        marginBottom: 12,
                        padding: 10,
                        background: "#0b1220",
                        borderRadius: 6,
                        border: "1px solid #243152",
                      }}
                    >
                      <div style={{ fontSize: 12, color: "#9ecfff" }}>
                        {asStr(c.doc_id) || asStr(c.snippet_id) || "ref"}
                      </div>
                      <div style={{ marginTop: 6, fontSize: 14 }}>
                        <ExpandableText
                          text={asStr(c.content) || "—"}
                          maxChars={200}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
          </Section>

          {approvalRequests.length > 0 ? (
            <Section title="Approval requests (pending human)">
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {approvalRequests.map((req, i) => (
                  <li key={i} style={{ marginBottom: 8 }}>
                    <code style={{ fontSize: 12 }}>{asStr(req.id) || "—"}</code>
                    {asStr(req.reason) ? (
                      <div style={{ fontSize: 13, marginTop: 4 }}>
                        <ExpandableText text={asStr(req.reason)} maxChars={160} />
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
              <p style={{ fontSize: 13, color: "#a7b4c9", marginBottom: 0 }}>
                Use <Link href="/approvals" style={{ color: "#9ecfff" }}>Approvals</Link> to approve or reject.
              </p>
            </Section>
          ) : null}

          {actResults.length > 0 ? (
            <Section title="Tool outcomes">
              <ul style={{ margin: 0, paddingLeft: 0, listStyle: "none" }}>
                {actResults.map((row, i) => {
                  const tool = asStr(row.tool);
                  const outcome = asStr(row.outcome);
                  const res = isRecord(row.result) ? row.result : null;
                  const compact =
                    res &&
                    (asStr(res.id) || asStr(res.title) || asStr(res.url) || asStr(res.pr_url));
                  return (
                    <li
                      key={i}
                      style={{
                        marginBottom: 12,
                        padding: 12,
                        background: "#0b1220",
                        borderRadius: 6,
                        border: "1px solid #243152",
                      }}
                    >
                      <div style={{ fontWeight: 600 }}>
                        {tool || "tool"}
                        <span style={{ color: "#7a8aa6", fontWeight: 400, marginLeft: 8 }}>
                          → {outcome || "?"}
                        </span>
                      </div>
                      {compact ? (
                        <div style={{ fontSize: 13, marginTop: 8, color: "#a7b4c9" }}>
                          {asStr(res.id) ? (
                            <span>
                              id: <code>{asStr(res.id)}</code>
                            </span>
                          ) : null}
                          {asStr(res.title) ? (
                            <div style={{ marginTop: 4 }}>
                              <ExpandableText text={asStr(res.title)} maxChars={120} />
                            </div>
                          ) : null}
                          {(asStr(res.url) || asStr(res.pr_url)) ? (
                            <div style={{ marginTop: 4 }}>
                              <a
                                href={asStr(res.url) || asStr(res.pr_url)}
                                style={{ color: "#9ecfff" }}
                                target="_blank"
                                rel="noreferrer"
                              >
                                Open link
                              </a>
                            </div>
                          ) : null}
                        </div>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </Section>
          ) : null}

          {isRecord(data.payload) && Object.keys(data.payload).length > 0 ? (
            <Section title="Incident payload (summary)">
              <p style={{ fontSize: 13, color: "#a7b4c9", marginTop: 0 }}>
                Shallow fields only — no internal prompts.
              </p>
              <dl style={{ ...dlStyle, margin: 0 }}>
                {Object.entries(data.payload).map(([k, v]) => (
                  <Fragment key={k}>
                    <dt>{k}</dt>
                    <dd>
                      {typeof v === "string" || typeof v === "number" ? (
                        <ExpandableText text={String(v)} maxChars={200} />
                      ) : Array.isArray(v) ? (
                        <code style={{ fontSize: 12 }}>{JSON.stringify(v)}</code>
                      ) : isRecord(v) ? (
                        <code style={{ fontSize: 12 }}>{JSON.stringify(v)}</code>
                      ) : (
                        String(v)
                      )}
                    </dd>
                  </Fragment>
                ))}
              </dl>
            </Section>
          ) : null}

          <Section title="Pipeline timeline (PS2.3)">
            <p style={{ fontSize: 13, color: "#a7b4c9", marginTop: 0 }}>
              Wall time per LangGraph node from <code>stage_timings</code> (saved with the run).
              Missing rows usually mean the node was not executed (e.g. escalation short-circuit).
              For span-level detail use Jaeger below.
            </p>
            {stageTimings.length === 0 ? (
              <p style={{ color: "#7a8aa6", marginBottom: 0 }}>
                No timeline data (older runs before PS2.3, or failed before first node completed).
              </p>
            ) : (
              <>
                <p style={{ fontSize: 13, marginTop: 0 }}>
                  <strong>Sum of stage wall times:</strong>{" "}
                  {formatStageDuration(timelineTotalMs)}
                </p>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                  <thead>
                    <tr style={{ textAlign: "left", borderBottom: "1px solid #30405f" }}>
                      <th style={{ padding: "6px 8px" }}>Stage</th>
                      <th style={{ padding: "6px 8px" }}>Duration</th>
                      <th style={{ padding: "6px 8px" }}>Outcome</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stageTimings.map((row, i) => (
                      <tr
                        key={`${row.node}-${i}`}
                        style={{ borderBottom: "1px solid #1f2a40" }}
                      >
                        <td style={{ padding: "8px", fontFamily: "monospace" }}>{row.node}</td>
                        <td style={{ padding: "8px" }}>
                          {formatStageDuration(row.duration_ms)}
                        </td>
                        <td
                          style={{
                            padding: "8px",
                            color: row.status === "error" ? "#ff9090" : "#b8e0b8",
                          }}
                        >
                          {row.status}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </Section>

          <Section title="Trace (Jaeger) — PS2.5">
            <p style={{ fontSize: 13, color: "#a7b4c9", marginTop: 0 }}>
              Same URL pattern as the agent report and{" "}
              <code style={{ fontSize: 12 }}>docs/runbooks/distributed_tracing_ps19.md</code> (
              <code>{`${JAEGER_UI_URL.replace(/\/$/, "")}/trace/{trace_id}`}</code>
              ). Opens in a new tab, not embedded.
            </p>
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li>
                <strong>Run ID</strong> (correlation):{" "}
                <code style={{ fontSize: 13 }}>{asStr(data.run_id) || "—"}</code>
              </li>
              <li>
                {traceUrl ? (
                  <a
                    href={traceUrl}
                    style={{ color: "#9ecfff" }}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View trace in Jaeger
                  </a>
                ) : (
                  <span style={{ color: "#7a8aa6" }}>
                    No trace link — this run has no valid <code>trace_id</code> /{" "}
                    <code>trace_link</code> (pre-OTel or export not reaching Jaeger).
                  </span>
                )}
              </li>
            </ul>
          </Section>

          <Section title="Replay from this run (PS2.6)">
            {!pipelineRunId ? (
              <p style={{ color: "#7a8aa6", marginTop: 0 }}>
                No <code>run_id</code> on this artifact — the replay API needs the pipeline UUID
                (see a successful run or <Link href="/replays" style={{ color: "#9ecfff" }}>Replay</Link>{" "}
                page).
              </p>
            ) : (
              <>
                <p style={{ fontSize: 13, color: "#a7b4c9", marginTop: 0 }}>
                  Calls <code>POST /replays/{"{run_id}"}/run</code> with this run&apos;s{" "}
                  <code>run_id</code>. Same diff logic as <code>scripts/replay_run.py</code> /{" "}
                  <code>replay_by_run_id</code>. Requires replay metadata under{" "}
                  <code>data/replay/runs/</code> for this id.
                </p>
                <p style={{ marginTop: 0 }}>
                  <strong>run_id:</strong>{" "}
                  <code style={{ fontSize: 13 }}>{pipelineRunId}</code>
                </p>
                <button
                  type="button"
                  disabled={replayLoading || Boolean(asStr(data.error))}
                  onClick={() => {
                    setReplayErr(null);
                    setReplayOut(null);
                    setReplayLoading(true);
                    void (async () => {
                      try {
                        const out = await postReplayRun(pipelineRunId);
                        setReplayOut(out);
                      } catch (e) {
                        setReplayErr(
                          e instanceof Error ? e.message : "Replay request failed",
                        );
                      } finally {
                        setReplayLoading(false);
                      }
                    })();
                  }}
                  style={{
                    padding: "10px 16px",
                    borderRadius: 6,
                    border: "none",
                    background: "#6b4f9e",
                    color: "#fff",
                    cursor: replayLoading || asStr(data.error) ? "not-allowed" : "pointer",
                    fontWeight: 600,
                    opacity: replayLoading || asStr(data.error) ? 0.6 : 1,
                  }}
                >
                  {replayLoading ? "Running replay…" : "Run replay & compare"}
                </button>
                {asStr(data.error) ? (
                  <p style={{ fontSize: 13, color: "#7a8aa6", marginBottom: 0 }}>
                    Disabled for failed runs (artifact may be incomplete).
                  </p>
                ) : null}
                {replayErr ? (
                  <p style={{ color: "#ff9090", marginBottom: 0, whiteSpace: "pre-wrap" }}>
                    {replayErr}
                  </p>
                ) : null}
                {replayOut ? (
                  <div style={{ marginTop: 16 }}>
                    <p style={{ marginTop: 0 }}>
                      <strong>New replay_run_id:</strong>{" "}
                      <code style={{ fontSize: 13 }}>
                        {replayOut.replay_run_id ? String(replayOut.replay_run_id) : "—"}
                      </code>{" "}
                      — check latest row on{" "}
                      <Link href="/incidents" style={{ color: "#9ecfff" }}>
                        Incidents
                      </Link>
                      .
                    </p>
                    {replayOut.comparison ? (
                      <ReplayComparisonSummary c={replayOut.comparison} />
                    ) : null}
                  </div>
                ) : null}
              </>
            )}
          </Section>

          <div style={{ marginTop: 32 }}>
            <button
              type="button"
              aria-expanded={showRaw}
              onClick={() => setShowRaw(!showRaw)}
              style={{
                background: "transparent",
                border: "1px solid #30405f",
                color: "#a7b4c9",
                padding: "8px 12px",
                borderRadius: 6,
                cursor: "pointer",
              }}
            >
              {showRaw ? "Hide" : "Show"} raw run JSON
            </button>
            {showRaw ? (
              <pre
                style={{
                  marginTop: 12,
                  background: "#111a2e",
                  padding: 16,
                  borderRadius: 8,
                  overflow: "auto",
                  fontSize: 11,
                  border: "1px solid #243152",
                  maxHeight: 360,
                }}
              >
                {JSON.stringify(data, null, 2)}
              </pre>
            ) : null}
          </div>
        </>
      ) : null}
    </main>
  );
}

const dlStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "140px 1fr",
  rowGap: 8,
  columnGap: 12,
  fontSize: 14,
  margin: 0,
};

const h3Style: CSSProperties = {
  fontSize: 14,
  textTransform: "capitalize",
  marginBottom: 8,
  color: "#c5d0e0",
};

const escalationSubheadingStyle: CSSProperties = {
  fontSize: 14,
  marginBottom: 6,
  marginTop: 0,
  color: "#c5d0e0",
};
