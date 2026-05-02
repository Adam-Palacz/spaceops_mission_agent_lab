"use client";

import { useEffect, useMemo, useState } from "react";
import { API_BASE_URL, APPROVAL_API_KEY } from "../../lib/config";

type ApprovalItem = {
  id: string;
  incident_id?: string;
  status: "pending" | "approved" | "rejected";
  decided_by?: string | null;
  decided_at?: string | null;
  reason?: string | null;
  step?: { action?: string; action_type?: string };
};

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  if (!resp.ok) {
    const message = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${message}`);
  }
  return (await resp.json()) as T;
}

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionState, setActionState] = useState<string>("");

  const pendingApprovals = useMemo(
    () => approvals.filter((a) => a.status === "pending"),
    [approvals]
  );

  const loadApprovals = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJson<{ approvals: ApprovalItem[] }>(
        `${API_BASE_URL}/approvals`,
        { headers: { "X-API-Key": APPROVAL_API_KEY } }
      );
      setApprovals(data.approvals || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const decideApproval = async (
    approvalId: string,
    decision: "approve" | "reject"
  ) => {
    setActionState(`${decision}:${approvalId}`);
    try {
      await fetchJson(`${API_BASE_URL}/approvals/${approvalId}/${decision}`, {
        method: "POST",
        headers: {
          "X-API-Key": APPROVAL_API_KEY,
          "X-Approval-By": "ui-operator",
        },
      });
      await loadApprovals();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setActionState("");
    }
  };

  useEffect(() => {
    void loadApprovals();
  }, []);

  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: 24 }}>
      <h1 style={{ marginBottom: 8 }}>Approvals</h1>
      <p style={{ marginTop: 0, color: "#a7b4c9" }}>
        API: <code>{API_BASE_URL}</code>
      </p>
      {!APPROVAL_API_KEY && (
        <p style={{ color: "#ffd27d" }}>
          Set <code>NEXT_PUBLIC_APPROVAL_API_KEY</code> to use approval actions.
        </p>
      )}

      <section style={{ marginTop: 24 }}>
        <h2>Pending</h2>
        {loading ? <p>Loading…</p> : null}
        {error ? <p style={{ color: "#ff9090" }}>{error}</p> : null}
        {!loading && !error && pendingApprovals.length === 0 ? (
          <p>No pending approvals.</p>
        ) : null}
        {!loading && !error && pendingApprovals.length > 0 ? (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #30405f" }}>
                <th style={{ padding: 8 }}>ID</th>
                <th style={{ padding: 8 }}>Incident</th>
                <th style={{ padding: 8 }}>Action</th>
                <th style={{ padding: 8 }}>Reason</th>
                <th style={{ padding: 8 }}>Controls</th>
              </tr>
            </thead>
            <tbody>
              {pendingApprovals.map((ap) => {
                const busy = actionState.endsWith(`:${ap.id}`);
                return (
                  <tr key={ap.id} style={{ borderBottom: "1px solid #1f2a40" }}>
                    <td style={{ padding: 8 }}>{ap.id}</td>
                    <td style={{ padding: 8 }}>{ap.incident_id || "—"}</td>
                    <td style={{ padding: 8 }}>
                      {ap.step?.action || ap.step?.action_type || "—"}
                    </td>
                    <td style={{ padding: 8 }}>{ap.reason || "—"}</td>
                    <td style={{ padding: 8 }}>
                      <button
                        type="button"
                        disabled={busy || !APPROVAL_API_KEY}
                        onClick={() => void decideApproval(ap.id, "approve")}
                        style={{ marginRight: 8 }}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        disabled={busy || !APPROVAL_API_KEY}
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
