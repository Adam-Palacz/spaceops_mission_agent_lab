"use client";

import { useEffect, useMemo, useState } from "react";

type RunItem = {
  id: string;
  incident_id: string;
  status: "completed" | "error";
  created_at: string;
  summary?: string | null;
  error?: string | null;
};

type ApprovalItem = {
  id: string;
  incident_id?: string;
  status: "pending" | "approved" | "rejected";
  decided_by?: string | null;
  decided_at?: string | null;
  reason?: string | null;
  step?: { action?: string; action_type?: string };
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_APPROVAL_API_KEY || "";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  if (!resp.ok) {
    const message = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${message}`);
  }
  return (await resp.json()) as T;
}

export default function HomePage() {
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [loadingApprovals, setLoadingApprovals] = useState(true);
  const [errorRuns, setErrorRuns] = useState<string | null>(null);
  const [errorApprovals, setErrorApprovals] = useState<string | null>(null);
  const [actionState, setActionState] = useState<string>("");

  const pendingApprovals = useMemo(
    () => approvals.filter((a) => a.status === "pending"),
    [approvals]
  );

  const loadRuns = async () => {
    setLoadingRuns(true);
    setErrorRuns(null);
    try {
      const data = await fetchJson<{ runs: RunItem[] }>(`${API_BASE_URL}/runs`);
      setRuns(data.runs || []);
    } catch (err) {
      setErrorRuns(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoadingRuns(false);
    }
  };

  const loadApprovals = async () => {
    setLoadingApprovals(true);
    setErrorApprovals(null);
    try {
      const data = await fetchJson<{ approvals: ApprovalItem[] }>(
        `${API_BASE_URL}/approvals`,
        {
          headers: { "X-API-Key": API_KEY }
        }
      );
      setApprovals(data.approvals || []);
    } catch (err) {
      setErrorApprovals(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoadingApprovals(false);
    }
  };

  const decideApproval = async (approvalId: string, decision: "approve" | "reject") => {
    setActionState(`${decision}:${approvalId}`);
    try {
      await fetchJson(`${API_BASE_URL}/approvals/${approvalId}/${decision}`, {
        method: "POST",
        headers: {
          "X-API-Key": API_KEY,
          "X-Approval-By": "ui-operator"
        }
      });
      await loadApprovals();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setErrorApprovals(msg);
    } finally {
      setActionState("");
    }
  };

  useEffect(() => {
    void loadRuns();
    void loadApprovals();
  }, []);

  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: 24 }}>
      <h1 style={{ marginBottom: 8 }}>SpaceOps Operator UI (P4.5)</h1>
      <p style={{ marginTop: 0, color: "#a7b4c9" }}>
        API: <code>{API_BASE_URL}</code>
      </p>
      {!API_KEY && (
        <p style={{ color: "#ffd27d" }}>
          Set <code>NEXT_PUBLIC_APPROVAL_API_KEY</code> to use approval actions.
        </p>
      )}

      <section style={{ marginTop: 24 }}>
        <h2>Incidents / Runs</h2>
        {loadingRuns ? <p>Loading runs...</p> : null}
        {errorRuns ? <p style={{ color: "#ff9090" }}>{errorRuns}</p> : null}
        {!loadingRuns && !errorRuns && runs.length === 0 ? (
          <p>No runs found.</p>
        ) : null}
        {!loadingRuns && !errorRuns && runs.length > 0 ? (
          <table width="100%" cellPadding={8} style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #30405f" }}>
                <th>Incident</th>
                <th>Status</th>
                <th>Summary/Error</th>
                <th>Created (UTC)</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} style={{ borderBottom: "1px solid #1f2a40" }}>
                  <td>{run.incident_id || "-"}</td>
                  <td>{run.status}</td>
                  <td>{run.summary || run.error || "-"}</td>
                  <td>{run.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </section>

      <section style={{ marginTop: 32 }}>
        <h2>Pending approvals</h2>
        {loadingApprovals ? <p>Loading approvals...</p> : null}
        {errorApprovals ? <p style={{ color: "#ff9090" }}>{errorApprovals}</p> : null}
        {!loadingApprovals && !errorApprovals && pendingApprovals.length === 0 ? (
          <p>No pending approvals.</p>
        ) : null}
        {!loadingApprovals && !errorApprovals && pendingApprovals.length > 0 ? (
          <table width="100%" cellPadding={8} style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #30405f" }}>
                <th>ID</th>
                <th>Incident</th>
                <th>Action</th>
                <th>Reason</th>
                <th>Controls</th>
              </tr>
            </thead>
            <tbody>
              {pendingApprovals.map((ap) => {
                const busy = actionState.endsWith(`:${ap.id}`);
                return (
                  <tr key={ap.id} style={{ borderBottom: "1px solid #1f2a40" }}>
                    <td>{ap.id}</td>
                    <td>{ap.incident_id || "-"}</td>
                    <td>{ap.step?.action || ap.step?.action_type || "-"}</td>
                    <td>{ap.reason || "-"}</td>
                    <td>
                      <button
                        disabled={busy || !API_KEY}
                        onClick={() => void decideApproval(ap.id, "approve")}
                        style={{ marginRight: 8 }}
                      >
                        Approve
                      </button>
                      <button
                        disabled={busy || !API_KEY}
                        onClick={() => void decideApproval(ap.id, "reject")}
                      >
                        Reject
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : null}
      </section>
    </main>
  );
}
