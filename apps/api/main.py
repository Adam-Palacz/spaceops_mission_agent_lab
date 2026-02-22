"""
SpaceOps Mission Agent Lab — API
GET /health, POST /ingest (NDJSON), POST /runs (trigger agent — stub).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Base path for data (repo root when run from repo)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data"

app = FastAPI(
    title="SpaceOps Mission Agent Lab API",
    description="Ingest, health, and run trigger for anomaly triage pipeline.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, str]:
    """Service is up. Returns 200."""
    return {"status": "ok", "service": "spaceops-api"}


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
        raise HTTPException(status_code=400, detail=f"Line {line_no}: invalid JSON — {e}")
    if not isinstance(obj, dict):
        raise HTTPException(status_code=400, detail=f"Line {line_no}: expected JSON object")
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
    payload: dict[str, Any] = Field(default_factory=dict, description="Incident payload (e.g. telemetry refs)")


@app.post("/runs")
def trigger_run(payload: RunTriggerPayload) -> JSONResponse:
    """
    Trigger an agent run. Runs Triage → Investigate → Decide → Report; returns report.
    """
    from apps.agent.graph import run_pipeline

    runs_dir = DATA_DIR / "incidents"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_file = runs_dir / f"run_{payload.incident_id}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    try:
        result = run_pipeline(payload.incident_id, payload.payload)
        report = result.get("report") or {}
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump({"incident_id": payload.incident_id, "payload": payload.payload, "report": report}, f, indent=2, ensure_ascii=False)
        return JSONResponse(status_code=200, content={"status": "completed", "incident_id": payload.incident_id, "report": report})
    except Exception as e:
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump({"incident_id": payload.incident_id, "payload": payload.payload, "error": str(e)}, f, indent=2, ensure_ascii=False)
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
