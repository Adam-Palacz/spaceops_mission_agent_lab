"""
SpaceOps Mission Agent Lab — API
GET /health, POST /ingest (NDJSON), POST /runs (trigger agent).
S1.10: OTel request spans; structured logging.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import time

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

from config import settings
from apps.telemetry import init_telemetry

# Base path for data (repo root when run from repo)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data"

app = FastAPI(
    title="SpaceOps Mission Agent Lab API",
    description="Ingest, health, and run trigger for anomaly triage pipeline.",
    version="0.1.0",
)

# P4.5 UI: allow browser calls from local Next.js app.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# S2.9 — Prometheus metrics (MoP1, MoP2)
# ---------------------------------------------------------------------------

AGENT_RUNS_TOTAL = Counter(
    "agent_runs_total",
    "Total number of agent runs triggered via /runs, labelled by status.",
    ["status"],
)
AGENT_RUN_DURATION_SECONDS = Histogram(
    "agent_run_duration_seconds",
    "Duration of agent runs in seconds.",
)
AGENT_ERRORS_TOTAL = Counter(
    "agent_errors_total",
    "Total number of agent run errors, labelled by error type.",
    ["type"],
)
AGENT_TOOL_CALLS_PER_RUN = Histogram(
    "agent_tool_calls_per_run",
    "Number of tool/LLM calls per agent run (llm_calls_used).",
    buckets=(0, 1, 2, 3, 5, 8, 13, 21, 34),
)


# S1.10: OTel request spans for /health, /ingest, /runs
init_telemetry(service_name="spaceops-api")
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, str]:
    """Service is up. Returns 200."""
    return {"status": "ok", "service": "spaceops-api"}


@app.get("/metrics")
def metrics() -> Response:
    """Expose Prometheus metrics for API/agent runs (S2.9)."""
    payload = generate_latest()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# Ingest (F1)
# ---------------------------------------------------------------------------


def _validate_ndjson_line(line: str, line_no: int) -> dict[str, Any]:
    """Parse one NDJSON line; raise HTTPException if invalid."""
    line = line.strip()
    if not line:
        raise HTTPException(status_code=400, detail=f"Line {line_no}: empty line")
    try:
        obj = json.loads(line)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400, detail=f"Line {line_no}: invalid JSON — {e}"
        )
    if not isinstance(obj, dict):
        raise HTTPException(
            status_code=400, detail=f"Line {line_no}: expected JSON object"
        )
    # Minimal schema: at least one key (e.g. timestamp or ts for traceability)
    if not obj:
        raise HTTPException(status_code=400, detail=f"Line {line_no}: empty object")
    return obj


def _persist_ndjson(source: str, records: list[dict[str, Any]]) -> Path:
    """Append records to data/{source}/; one file per ingest with timestamp."""
    allowed = ("telemetry", "events", "ground_logs")
    if source not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"source must be one of {allowed}",
        )
    out_dir = DATA_DIR / source
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_file = out_dir / f"ingest_{ts}.ndjson"
    with open(out_file, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return out_file


@app.post("/ingest")
async def ingest(
    request: Request,
    source: str = Query(..., description="One of: telemetry, events, ground_logs"),
) -> JSONResponse:
    """
    Accept NDJSON body (newline-delimited JSON lines). Validate each line; persist to data/{source}/.
    """
    body = (await request.body()).decode("utf-8")
    lines = [ln for ln in body.strip().split("\n") if ln.strip()]
    if not lines:
        raise HTTPException(status_code=400, detail="Empty body or no NDJSON lines")
    records = []
    for i, line in enumerate(lines, start=1):
        records.append(_validate_ndjson_line(line, i))
    path = _persist_ndjson(source, records)
    return JSONResponse(
        status_code=201,
        content={
            "status": "created",
            "source": source,
            "records": len(records),
            "path": str(path.relative_to(REPO_ROOT)),
        },
    )


# ---------------------------------------------------------------------------
# Run trigger (S1.7 — invokes LangGraph pipeline)
# ---------------------------------------------------------------------------


class RunTriggerPayload(BaseModel):
    """Payload for triggering an agent run."""

    incident_id: str = Field(..., min_length=1, description="Incident identifier")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Incident payload (e.g. telemetry refs)"
    )


@app.post("/runs")
def trigger_run(payload: RunTriggerPayload) -> JSONResponse:
    """
    Trigger an agent run. Runs Triage → Investigate → Decide → Report; returns report.
    """
    from apps.agent.graph import run_pipeline

    runs_dir = DATA_DIR / "incidents"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_file = (
        runs_dir
        / f"run_{payload.incident_id}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    started = time.perf_counter()
    try:
        result = run_pipeline(payload.incident_id, payload.payload)
        report = result.get("report") or {}
        duration = max(0.0, time.perf_counter() - started)
        AGENT_RUNS_TOTAL.labels(status="success").inc()
        AGENT_RUN_DURATION_SECONDS.observe(duration)
        calls = int(result.get("llm_calls_used") or 0)
        if calls >= 0:
            AGENT_TOOL_CALLS_PER_RUN.observe(calls)
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "incident_id": payload.incident_id,
                    "payload": payload.payload,
                    "report": report,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        return JSONResponse(
            status_code=200,
            content={
                "status": "completed",
                "incident_id": payload.incident_id,
                "report": report,
            },
        )
    except Exception as e:
        duration = max(0.0, time.perf_counter() - started)
        AGENT_RUNS_TOTAL.labels(status="error").inc()
        AGENT_RUN_DURATION_SECONDS.observe(duration)
        AGENT_ERRORS_TOTAL.labels(type=e.__class__.__name__).inc()
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "incident_id": payload.incident_id,
                    "payload": payload.payload,
                    "error": str(e),
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")


@app.get("/runs")
def list_runs(limit: int = Query(20, ge=1, le=200)) -> JSONResponse:
    """
    List recent incident runs persisted by POST /runs.

    Returns lightweight metadata for UI usage (P4.5):
    - incident_id
    - status (completed/error)
    - created_at (from file mtime)
    - report summary or error message when available
    """
    runs_dir = DATA_DIR / "incidents"
    if not runs_dir.exists():
        return JSONResponse(status_code=200, content={"runs": []})

    out: list[dict[str, Any]] = []
    files = sorted(
        runs_dir.glob("run_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in files[:limit]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            # Keep endpoint robust even if one run file is malformed.
            continue
        report = payload.get("report")
        error = payload.get("error")
        if isinstance(report, dict):
            summary = report.get("summary")
        else:
            summary = None
        created_at = datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        ).isoformat()
        out.append(
            {
                "id": path.stem,
                "incident_id": payload.get("incident_id", ""),
                "status": "completed" if error is None else "error",
                "created_at": created_at,
                "summary": summary,
                "error": error,
            }
        )
    return JSONResponse(status_code=200, content={"runs": out})


# ---------------------------------------------------------------------------
# S2.5 Approval API (idempotent, auth, audit)
# ---------------------------------------------------------------------------


def _approval_auth(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    authorization: str | None = Header(None),
) -> str:
    """
    Validate API key for approve/reject; return identity for audit (who).
    Accepts X-API-Key or Authorization: Bearer <key>. If X-Approval-By is used, that becomes 'who'.
    """
    expected = (getattr(settings, "approval_api_key", None) or "").strip()
    if not expected:
        raise HTTPException(
            status_code=501,
            detail="Approval API key not configured (set APPROVAL_API_KEY)",
        )
    token: str | None = None
    if x_api_key:
        token = x_api_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token or token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return "authenticated"


def _approval_identity(
    request: Request,
    _auth: str = Depends(_approval_auth),
) -> str:
    """Return 'who' for audit: X-Approval-By header or fallback to 'authenticated'."""
    who = request.headers.get("X-Approval-By", "").strip()
    return who or _auth


@app.get("/approvals")
def list_approvals(
    status: str | None = Query(None, description="Filter: pending, approved, rejected"),
    _: str = Depends(_approval_auth),
) -> JSONResponse:
    """List approval requests; optional filter by status. Requires API key."""
    from apps.agent.approval_store import list_requests

    requests = list_requests(status=status)
    return JSONResponse(status_code=200, content={"approvals": requests})


@app.post("/approvals/{approval_id}/approve")
def approve_request(
    approval_id: str,
    who: str = Depends(_approval_identity),
) -> JSONResponse:
    """
    Mark approval request as approved and execute the stored action once (S2.6).
    Idempotent: already approved/rejected returns 200 without re-execution.
    Requires X-API-Key or Authorization: Bearer. Optional X-Approval-By for audit 'who'.
    """
    from apps.agent.approval_store import approve as store_approve
    from apps.agent.approval_store import get_request
    from apps.agent.approval_executor import execute_approved_action
    from apps.agent.audit_log import append_entry as audit_append

    rec_before = get_request(approval_id)
    if rec_before is None:
        raise HTTPException(status_code=404, detail="Approval request not found")

    was_pending = rec_before.get("status") == "pending"
    rec = store_approve(approval_id, decided_by=who)
    if rec is None:
        raise HTTPException(status_code=404, detail="Approval request not found")

    audit_append(
        trace_id=approval_id,
        incident_id=rec.get("incident_id", ""),
        actor="human",
        tool="approve",
        args={
            "approval_id": approval_id,
            "approval_request_id": approval_id,
            "decided_by": who,
        },
        decision="approve",
        policy_result="n/a",
        outcome="success",
    )

    execution_result = None
    if was_pending:
        execution_result = execute_approved_action(approval_id, rec_before)
        audit_append(
            trace_id=approval_id,
            incident_id=rec.get("incident_id", ""),
            actor="agent",
            tool="execute_restricted",
            args={
                "approval_id": approval_id,
                "step_index": rec_before.get("step_index"),
            },
            decision="allow",
            outcome=execution_result.get("outcome", "failure"),
            error_message=execution_result.get("error_message"),
        )

    content = {"status": "approved", "approval": rec}
    if execution_result is not None:
        content["execution"] = {
            "outcome": execution_result.get("outcome", "failure"),
            "result": execution_result.get("result"),
            "error_message": execution_result.get("error_message"),
        }
    return JSONResponse(status_code=200, content=content)


@app.post("/approvals/{approval_id}/reject")
def reject_request(
    approval_id: str,
    who: str = Depends(_approval_identity),
) -> JSONResponse:
    """
    Mark approval request as rejected. Idempotent: already approved/rejected returns 200.
    Requires X-API-Key or Authorization: Bearer. Optional X-Approval-By for audit 'who'.
    """
    from apps.agent.approval_store import reject as store_reject
    from apps.agent.audit_log import append_entry as audit_append

    rec = store_reject(approval_id, decided_by=who)
    if rec is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    audit_append(
        trace_id=approval_id,
        incident_id=rec.get("incident_id", ""),
        actor="human",
        tool="reject",
        args={
            "approval_id": approval_id,
            "approval_request_id": approval_id,
            "decided_by": who,
        },
        decision="reject",
        policy_result="n/a",
        outcome="success",
    )
    return JSONResponse(
        status_code=200, content={"status": "rejected", "approval": rec}
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
