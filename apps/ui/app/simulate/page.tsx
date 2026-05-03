"use client";

import type { CSSProperties, FormEvent, ReactNode } from "react";
import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { API_BASE_URL, SUBSYSTEM_OPTIONS } from "../../lib/config";

type Mode = "form" | "file";

const SCENARIO_OPTIONS = ["fixture", "no-data", "test"] as const;
type ScenarioRef = (typeof SCENARIO_OPTIONS)[number];

const RISK_OPTIONS = ["low", "medium", "high"] as const;
type RiskLevel = (typeof RISK_OPTIONS)[number];

const MAX_BYTES = 52 * 1024;

type SubsystemChoice = Exclude<(typeof SUBSYSTEM_OPTIONS)[number], "">;

async function postSimulateFormData(fd: FormData): Promise<{
  text: string;
  runKey: string | null;
}> {
  const resp = await fetch(`${API_BASE_URL}/runs/simulate`, {
    method: "POST",
    body: fd,
  });
  const text = await resp.text();
  if (!resp.ok) {
    throw new Error(`${resp.status}: ${text}`);
  }
  let runKey: string | null = null;
  try {
    const j = JSON.parse(text) as { run_key?: string };
    if (j.run_key) runKey = j.run_key;
  } catch {
    /* ignore */
  }
  return { text, runKey };
}

export default function SimulateFixturePage() {
  const subsystemChoices = useMemo(
    () => SUBSYSTEM_OPTIONS.filter((s): s is SubsystemChoice => s !== ""),
    [],
  );

  const [mode, setMode] = useState<Mode>("form");
  const [file, setFile] = useState<File | null>(null);

  const [declaredIncidentId, setDeclaredIncidentId] = useState("demo-sim-1");
  const [scenarioRef, setScenarioRef] = useState<ScenarioRef>("fixture");
  const [subsystemHint, setSubsystemHint] = useState(subsystemChoices[0] ?? "Power");
  const [riskLevel, setRiskLevel] = useState<RiskLevel>("medium");
  const [timeRangeStart, setTimeRangeStart] = useState("2025-02-14T09:00:00Z");
  const [timeRangeEnd, setTimeRangeEnd] = useState("2025-02-14T11:00:00Z");
  const [channels, setChannels] = useState("");
  const [message, setMessage] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultText, setResultText] = useState<string | null>(null);
  const [runKey, setRunKey] = useState<string | null>(null);

  const onSubmit = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      setError(null);
      setResultText(null);
      setRunKey(null);
      setLoading(true);
      try {
        if (mode === "file") {
          if (!file) {
            setError("Wybierz plik .json (max ~48 KiB).");
            return;
          }
          if (file.size > MAX_BYTES) {
            setError("Plik za duży — max ok. 48 KiB.");
            return;
          }
          const fd = new FormData();
          fd.append("file", file, file.name || "fixture.json");
          const out = await postSimulateFormData(fd);
          setResultText(out.text);
          setRunKey(out.runKey);
          return;
        }

        const id = declaredIncidentId.trim();
        if (!id) {
          setError("Wpisz etykietę incydentu (tylko litery, cyfry, ._- ).");
          return;
        }
        if (!/^[A-Za-z0-9._-]+$/.test(id)) {
          setError("Niedozwolone znaki w etykiecie — użyj A–Z, 0–9, ._-");
          return;
        }

        const body: Record<string, unknown> = {
          declared_incident_id: id,
          scenario_ref: scenarioRef,
          subsystem_hint: subsystemHint,
          risk_level: riskLevel,
          time_range_start: timeRangeStart.trim(),
          time_range_end: timeRangeEnd.trim(),
        };
        const ch = channels.trim();
        if (ch) body.channels = ch;
        const msg = message.trim();
        if (msg) body.message = msg;

        const resp = await fetch(`${API_BASE_URL}/runs/simulate/quick`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const text = await resp.text();
        if (!resp.ok) {
          throw new Error(`${resp.status}: ${text}`);
        }
        setResultText(text);
        try {
          const j = JSON.parse(text) as { run_key?: string };
          if (j.run_key) setRunKey(j.run_key);
        } catch {
          /* ignore */
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Request failed");
      } finally {
        setLoading(false);
      }
    },
    [
      mode,
      file,
      declaredIncidentId,
      scenarioRef,
      subsystemHint,
      riskLevel,
      timeRangeStart,
      timeRangeEnd,
      channels,
      message,
    ],
  );

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: 24 }}>
      <p style={{ marginTop: 0 }}>
        <Link href="/incidents" style={{ color: "#9ecfff" }}>
          ← Incidents
        </Link>
      </p>
      <h1 style={{ marginBottom: 8 }}>Symulacja (fixture)</h1>
      <p style={{ color: "#a7b4c9", marginTop: 0, fontSize: 14 }}>
        Tryb <strong>formularz</strong>: wybierasz wartości — backend składa JSON <code>payload</code> i
        wywołuje <code>POST /runs/simulate/quick</code>. Tryb <strong>plik</strong>: jak wcześniej{" "}
        <code>POST /runs/simulate</code>. Pipeline zawsze dostaje syntetyczny{" "}
        <code>sim-upload-…</code>.
      </p>

      <div style={{ marginBottom: 16, display: "flex", gap: 16, flexWrap: "wrap" }}>
        <label style={radioLabel}>
          <input
            type="radio"
            name="sim-mode"
            checked={mode === "form"}
            onChange={() => setMode("form")}
          />{" "}
          Formularz (wymagane pola)
        </label>
        <label style={radioLabel}>
          <input
            type="radio"
            name="sim-mode"
            checked={mode === "file"}
            onChange={() => setMode("file")}
          />{" "}
          Upload własnego JSON
        </label>
      </div>

      <form
        onSubmit={(ev) => void onSubmit(ev)}
        style={{
          padding: 16,
          background: "#111a2e",
          borderRadius: 8,
          border: "1px solid #243152",
        }}
      >
        {mode === "form" ? (
          <>
            <Field label="Etykieta incydentu (logiczna)" hint="Wzorzec: A–Z, cyfry, ._- — nie myl z sim-upload-…">
              <input
                type="text"
                required
                value={declaredIncidentId}
                onChange={(ev) => setDeclaredIncidentId(ev.target.value)}
                style={inputStyle}
                spellCheck={false}
                autoComplete="off"
              />
            </Field>
            <Field label="Scenariusz (payload.ref)" hint="Jak w testach pipeline">
              <select
                required
                value={scenarioRef}
                onChange={(ev) =>
                  setScenarioRef(ev.target.value as ScenarioRef)
                }
                style={inputStyle}
              >
                {SCENARIO_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Subsystem (hint w payload)" hint="Wpisywane do payload dla KB / sygnatury">
              <select
                required
                value={subsystemHint}
                onChange={(ev) =>
                  setSubsystemHint(ev.target.value as SubsystemChoice)
                }
                style={inputStyle}
              >
                {subsystemChoices.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Ryzyko (payload.risk)" hint="Startowy poziom w payload">
              <select
                required
                value={riskLevel}
                onChange={(ev) => setRiskLevel(ev.target.value as RiskLevel)}
                style={inputStyle}
              >
                {RISK_OPTIONS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Time range start (ISO)" hint="Okno telemetryczne dla MCP">
              <input
                type="text"
                required
                value={timeRangeStart}
                onChange={(ev) => setTimeRangeStart(ev.target.value)}
                style={inputStyle}
              />
            </Field>
            <Field label="Time range end (ISO)" hint="Okno telemetryczne dla MCP">
              <input
                type="text"
                required
                value={timeRangeEnd}
                onChange={(ev) => setTimeRangeEnd(ev.target.value)}
                style={inputStyle}
              />
            </Field>
            <Field label="Kanały (opcjonalnie)" hint="Lista rozdzielona przecinkami → payload.channels">
              <input
                type="text"
                value={channels}
                onChange={(ev) => setChannels(ev.target.value)}
                placeholder="np. power.bus_voltage, thermal.plate_t"
                style={inputStyle}
              />
            </Field>
            <Field label="Wiadomość (opcjonalnie)" hint="Krótki opis → payload.message">
              <input
                type="text"
                value={message}
                onChange={(ev) => setMessage(ev.target.value)}
                placeholder="np. spadek napięcia na szynie"
                style={inputStyle}
              />
            </Field>
          </>
        ) : (
          <label style={{ display: "block", marginBottom: 12, fontSize: 14 }}>
            <span style={{ display: "block", marginBottom: 6 }}>Plik JSON (incident_id + payload)</span>
            <input
              type="file"
              accept="application/json,.json,text/plain"
              onChange={(ev) => {
                const f = ev.target.files?.[0];
                setFile(f ?? null);
              }}
              style={{ fontSize: 14, color: "#e7edf7" }}
            />
          </label>
        )}
        <button
          type="submit"
          disabled={loading}
          style={{
            marginTop: 8,
            padding: "10px 18px",
            borderRadius: 6,
            border: "none",
            background: "#2a6fdb",
            color: "#fff",
            cursor: loading ? "wait" : "pointer",
            fontWeight: 600,
          }}
        >
          {loading ? "Uruchamianie…" : mode === "form" ? "Symuluj z formularza" : "Wyślij plik"}
        </button>
      </form>

      {error ? (
        <p style={{ color: "#ff9090", marginTop: 16, whiteSpace: "pre-wrap" }}>{error}</p>
      ) : null}

      {runKey ? (
        <p style={{ marginTop: 16 }}>
          <Link
            href={`/incidents/${encodeURIComponent(runKey)}`}
            style={{ color: "#9ecfff", fontWeight: 600 }}
          >
            Szczegóły runu →
          </Link>
        </p>
      ) : null}

      {resultText ? (
        <pre
          style={{
            marginTop: 16,
            padding: 14,
            background: "#0b1220",
            borderRadius: 8,
            border: "1px solid #243152",
            fontSize: 12,
            overflow: "auto",
            maxHeight: 360,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {resultText}
        </pre>
      ) : null}

      <p style={{ fontSize: 12, color: "#7a8aa6", marginTop: 24 }}>
        NDJSON telemetrii: <code>POST /ingest</code>. Dokumentacja:{" "}
        <code>docs/runbooks/fixture_upload_simulation.md</code>.
      </p>
    </main>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint: string;
  children: ReactNode;
}) {
  return (
    <label style={{ display: "block", marginBottom: 14, fontSize: 14 }}>
      <span style={{ display: "block", marginBottom: 4, fontWeight: 500 }}>{label}</span>
      <span style={{ display: "block", marginBottom: 6, fontSize: 12, color: "#7a8aa6" }}>
        {hint}
      </span>
      {children}
    </label>
  );
}

const radioLabel: CSSProperties = {
  fontSize: 14,
  cursor: "pointer",
  color: "#e7edf7",
};

const inputStyle: CSSProperties = {
  width: "100%",
  maxWidth: "100%",
  boxSizing: "border-box",
  padding: "10px 12px",
  borderRadius: 6,
  border: "1px solid #30405f",
  background: "#0b1220",
  color: "#e7edf7",
};
