/**
 * PS2.5 — Jaeger UI deep links (same pattern as agent `report.trace_link` / runbook PS1.9).
 * Format: `{jaegerRoot}/trace/{32-char-hex-trace-id}` (no query string).
 */

export function isValidJaegerTraceIdHex(traceId: string): boolean {
  const t = traceId.trim();
  return t.length === 32 && /^[a-f0-9]{32}$/i.test(t);
}

/**
 * Prefer absolute `trace_link` from the report when it looks like a URL; otherwise build
 * from `trace_id` and `NEXT_PUBLIC_JAEGER_UI_URL` (default Jaeger UI on :16686).
 */
export function buildJaegerTraceHref(options: {
  jaegerUiRoot: string;
  traceLink?: string | null;
  traceId?: string | null;
}): string | null {
  const tl = (options.traceLink || "").trim();
  if (tl.startsWith("http://") || tl.startsWith("https://")) {
    return tl;
  }
  const tid = (options.traceId || "").trim();
  if (isValidJaegerTraceIdHex(tid)) {
    const base = options.jaegerUiRoot.replace(/\/$/, "");
    return `${base}/trace/${tid}`;
  }
  return null;
}
