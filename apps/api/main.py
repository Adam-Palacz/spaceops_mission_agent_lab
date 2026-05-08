"""
SpaceOps Mission Agent Lab — API
GET /health, POST /ingest (NDJSON), POST /runs (trigger agent).
S1.10: OTel request spans; structured logging.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import json
import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
import time

from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
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
from apps.contracts.v1 import TelemetryEventV1
from apps.telemetry import init_telemetry

# Base path for data (repo root when run from repo)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data"

# PS2.7: fixture upload — UTF-8 JSON only, bounded size (threat model in docs).
FIXTURE_UPLOAD_MAX_BYTES = 48 * 1024
SIM_INCIDENT_PREFIX = "sim-upload-"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from apps.ingest_jetstream import close_nats

    await close_nats(app)


app = FastAPI(
    title="SpaceOps Mission Agent Lab API",
    description="Ingest, health, and run trigger for anomaly triage pipeline.",
    version="0.1.0",
    lifespan=lifespan,
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
INGEST_EVENTS_TOTAL = Counter(
    "ingest_events_total",
    "Total ingest records processed, by outcome.",
    ["outcome"],
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


@app.get("/dlq/telemetry")
def dlq_telemetry(limit: int = Query(100, ge=1, le=1000)) -> dict[str, Any]:
    """
    PS3.3 read-only DLQ inspection endpoint.

    Returns latest dead-letter rows emitted by telemetry persister.
    """
    import psycopg2

    from apps.workers.telemetry_persist import list_dlq_events

    try:
        conn = psycopg2.connect(settings.postgres_dsn)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"DLQ unavailable: cannot connect to Postgres ({exc})",
        ) from exc
    try:
        rows = list_dlq_events(conn, limit=limit)
        return {"dlq_events": rows, "count": len(rows)}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Ingest (F1)
# ---------------------------------------------------------------------------


def _validate_ndjson_line(line: str, line_no: int) -> dict[str, Any]:
    """Parse one NDJSON line; raise HTTPException if invalid JSON payload."""
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
    if not obj:
        raise HTTPException(status_code=400, detail=f"Line {line_no}: empty object")
    return obj


def _canonical_json_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_telemetry_record(raw: dict[str, Any], source: str) -> TelemetryEventV1:
    """
    Convert legacy-ish telemetry payload into TelemetryEventV1.

    We accept older fixture shapes by mapping:
    - timestamp -> ts
    - channel_id -> channel
    - missing event_id -> deterministic hash fallback
    """
    candidate = dict(raw)
    if "ts" not in candidate and isinstance(candidate.get("timestamp"), str):
        candidate["ts"] = candidate["timestamp"]
    if "channel" not in candidate and isinstance(candidate.get("channel_id"), str):
        candidate["channel"] = candidate["channel_id"]
    if "event_id" not in candidate or not str(candidate.get("event_id")).strip():
        candidate["event_id"] = f"legacy-{_canonical_json_hash(raw)}"
    if "source" not in candidate or not str(candidate.get("source") or "").strip():
        candidate["source"] = source
    return TelemetryEventV1.model_validate(candidate)


def _load_existing_event_ids(out_dir: Path) -> set[str]:
    """Load known event_id values from existing NDJSON files for dedupe."""
    event_ids: set[str] = set()
    if not out_dir.exists():
        return event_ids
    for path in sorted(out_dir.glob("*.ndjson")):
        try:
            with path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        event_id = obj.get("event_id")
                        if isinstance(event_id, str) and event_id.strip():
                            event_ids.add(event_id.strip())
        except OSError:
            continue
    return event_ids


def _persist_ndjson(
    source: str, records: list[dict[str, Any]]
) -> tuple[Path, int, int]:
    """Persist deduplicated records to data/{source}/ and return (path, accepted, duplicates)."""
    allowed = ("telemetry", "events", "ground_logs")
    if source not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"source must be one of {allowed}",
        )
    out_dir = DATA_DIR / source
    out_dir.mkdir(parents=True, exist_ok=True)
    existing_event_ids = _load_existing_event_ids(out_dir)
    seen_in_batch: set[str] = set()
    deduped: list[dict[str, Any]] = []
    duplicates = 0
    for rec in records:
        event_id = str(rec.get("event_id") or "").strip()
        if not event_id:
            event_id = f"legacy-{_canonical_json_hash(rec)}"
            rec = {**rec, "event_id": event_id}
        if event_id in existing_event_ids or event_id in seen_in_batch:
            duplicates += 1
            continue
        seen_in_batch.add(event_id)
        deduped.append(rec)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_file = out_dir / f"ingest_{ts}.ndjson"
    with open(out_file, "w", encoding="utf-8") as f:
        for rec in deduped:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return out_file, len(deduped), duplicates


@app.post("/ingest")
async def ingest(
    request: Request,
    source: str = Query(..., description="One of: telemetry, events, ground_logs"),
) -> JSONResponse:
    """
    Accept NDJSON (newline-delimited JSON).

    - **telemetry** + ``NATS_URL`` set → validate, publish to JetStream (ADR 0002), **202 Accepted**
      after broker ack (Postgres filled asynchronously by ``telemetry-persister`` worker).
    - **telemetry** without NATS → legacy NDJSON files under ``data/{source}/``, **201 Created**.
    - **events** / **ground_logs** → files only (**201**) until a later PS extends JetStream.
    """
    body = (await request.body()).decode("utf-8")
    lines = [ln for ln in body.strip().split("\n") if ln.strip()]
    if not lines:
        raise HTTPException(status_code=400, detail="Empty body or no NDJSON lines")
    records: list[dict[str, Any]] = []
    validation_errors: list[str] = []
    for i, line in enumerate(lines, start=1):
        raw = _validate_ndjson_line(line, i)
        if source != "telemetry":
            # PS1.2 focuses on telemetry contract hardening.
            records.append(raw)
            continue
        try:
            contract = _normalize_telemetry_record(raw, source=source)
            records.append(contract.model_dump())
        except Exception as exc:
            validation_errors.append(f"Line {i}: {exc}")
    if validation_errors:
        INGEST_EVENTS_TOTAL.labels(outcome="rejected").inc(len(validation_errors))
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_failed",
                "source": source,
                "rejected": len(validation_errors),
                "messages": validation_errors[:20],
            },
        )

    if source == "telemetry" and settings.nats_url.strip():
        from apps.ingest_jetstream import get_or_create_js, publish_telemetry_records

        try:
            js = await get_or_create_js(request.app)
            accepted_new, dup_batch, dup_broker = await publish_telemetry_records(
                js, records
            )
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={"error": "ingest_unavailable", "message": str(exc)},
            ) from exc

        dup_total = dup_batch + dup_broker
        if accepted_new:
            INGEST_EVENTS_TOTAL.labels(outcome="accepted").inc(accepted_new)
        if dup_total:
            INGEST_EVENTS_TOTAL.labels(outcome="duplicate").inc(dup_total)
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "source": source,
                "ingest_mode": "jetstream",
                "records": len(records),
                "accepted": accepted_new,
                "duplicates": dup_total,
                "rejected": 0,
            },
        )

    path, accepted_count, duplicate_count = _persist_ndjson(source, records)
    if accepted_count:
        INGEST_EVENTS_TOTAL.labels(outcome="accepted").inc(accepted_count)
    if duplicate_count:
        INGEST_EVENTS_TOTAL.labels(outcome="duplicate").inc(duplicate_count)
    return JSONResponse(
        status_code=201,
        content={
            "status": "created",
            "source": source,
            "records": accepted_count,
            "accepted": accepted_count,
            "duplicates": duplicate_count,
            "rejected": 0,
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


class ResumeRunPayload(BaseModel):
    """PS3.9: operator-triggered resume of a run with same run_id."""

    run_id: str = Field(..., min_length=1, description="Existing pipeline run_id")
    incident_id: str = Field(..., min_length=1, description="Incident identifier")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Same/safe payload needed to continue context"
    )


class SimulateQuickFormPayload(BaseModel):
    """
    PS2.7 — Prosty formularz: backend składa `payload` dla `run_pipeline`.
    Wszystkie listy/selecty walidowane przez Pydantic (422 przy braku/brakach).
    """

    declared_incident_id: str = Field(
        ...,
        min_length=1,
        max_length=120,
        pattern=r"^[A-Za-z0-9._-]+$",
        description="Etykieta logiczna (run i tak dostaje sim-upload-…).",
    )
    scenario_ref: Literal["fixture", "no-data", "test"] = Field(
        ...,
        description="payload.ref — wybór scenariusza jak w evalach.",
    )
    subsystem_hint: Literal[
        "ADCS", "Power", "Thermal", "Comms", "Payload", "Ground"
    ] = Field(...)
    risk_level: Literal["low", "medium", "high"] = Field(...)
    time_range_start: str = Field(
        default="2025-02-14T09:00:00Z",
        min_length=1,
        max_length=80,
    )
    time_range_end: str = Field(
        default="2025-02-14T11:00:00Z",
        min_length=1,
        max_length=80,
    )
    channels: str | None = Field(
        None,
        max_length=800,
        description="Opcjonalnie: kanały telemetryczne, przecinki.",
    )
    message: str | None = Field(
        None,
        max_length=500,
        description="Opcjonalnie: krótki opis (hint KB).",
    )

    def build_payload(self) -> dict[str, Any]:
        pl: dict[str, Any] = {
            "ref": self.scenario_ref,
            "subsystem": self.subsystem_hint,
            "risk": self.risk_level,
            "time_range_start": self.time_range_start.strip(),
            "time_range_end": self.time_range_end.strip(),
        }
        if self.channels and self.channels.strip():
            parts = [c.strip() for c in self.channels.split(",") if c.strip()]
            if parts:
                pl["channels"] = parts
        if self.message and self.message.strip():
            pl["message"] = self.message.strip()
        return pl


def _safe_upload_basename(name: str | None) -> str:
    """Strip path components and control chars; never trust client filenames."""
    if not name or not str(name).strip():
        return "fixture.json"
    base = Path(str(name)).name
    if not base or base in (".", ".."):
        return "fixture.json"
    cleaned = re.sub(r"[^\w.\-]+", "_", base, flags=re.UNICODE).strip("._")[:120]
    if not cleaned:
        return "fixture.json"
    if not cleaned.lower().endswith(".json"):
        return f"{cleaned}.json"
    return cleaned


def _slug_for_sim_incident_id(declared: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", declared.strip()).strip("-")
    return (s[:48] if s else "inc") or "inc"


def _build_sim_incident_id(declared_incident_id: str) -> str:
    """Isolated incident_id so fixture runs do not collide with production ids (PS2.7)."""
    slug = _slug_for_sim_incident_id(declared_incident_id)
    token = uuid.uuid4().hex[:10]
    return f"{SIM_INCIDENT_PREFIX}{token}-{slug}"


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
        result = run_pipeline(payload.incident_id, payload.payload, replay_source="api")
        report = result.get("report") or {}
        run_id = str(result.get("run_id") or "")
        duration = max(0.0, time.perf_counter() - started)
        AGENT_RUNS_TOTAL.labels(status="success").inc()
        AGENT_RUN_DURATION_SECONDS.observe(duration)
        calls = int(result.get("llm_calls_used") or 0)
        if calls >= 0:
            AGENT_TOOL_CALLS_PER_RUN.observe(calls)
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "run_id": run_id,
                    "incident_id": payload.incident_id,
                    "payload": payload.payload,
                    "report": report,
                    "subsystem": str(result.get("subsystem") or ""),
                    "risk": str(result.get("risk") or ""),
                    "escalated": bool(result.get("escalated")),
                    "trace_id": str(result.get("trace_id") or ""),
                    "stage_timings": result.get("stage_timings") or [],
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        return JSONResponse(
            status_code=200,
            content={
                "status": "completed",
                "run_id": run_id,
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


@app.post("/runs/resume")
def resume_run(payload: ResumeRunPayload) -> JSONResponse:
    """
    PS3.9: Operator action to resume a checkpointed run with same run_id.
    Requires durable checkpoints enabled and Postgres reachable.
    """
    from apps.agent.graph import run_pipeline

    try:
        result = run_pipeline(
            payload.incident_id,
            payload.payload,
            replay_source="resume",
            run_id=payload.run_id,
            resume=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume failed: {e}") from e
    return JSONResponse(
        status_code=200,
        content={
            "status": "resumed",
            "run_id": str(result.get("run_id") or payload.run_id),
            "incident_id": payload.incident_id,
            "report": result.get("report") or {},
        },
    )


def _simulate_run_core(
    declared_incident_id: str,
    payload: dict[str, Any],
    fixture_upload_label: str,
) -> JSONResponse:
    """Shared simulate persistence + metrics (PS2.7): file upload i formularz JSON."""
    from apps.agent.graph import run_pipeline

    declared = str(declared_incident_id).strip()
    pl = dict(payload)
    sim_incident_id = _build_sim_incident_id(declared)
    runs_dir = DATA_DIR / "incidents"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_file = (
        runs_dir
        / f"run_{sim_incident_id}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    upload_name = _safe_upload_basename(fixture_upload_label)
    started = time.perf_counter()
    try:
        result = run_pipeline(sim_incident_id, pl, replay_source="fixture_sim")
        report = result.get("report") or {}
        run_id = str(result.get("run_id") or "")
        duration = max(0.0, time.perf_counter() - started)
        AGENT_RUNS_TOTAL.labels(status="success").inc()
        AGENT_RUN_DURATION_SECONDS.observe(duration)
        calls = int(result.get("llm_calls_used") or 0)
        if calls >= 0:
            AGENT_TOOL_CALLS_PER_RUN.observe(calls)
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "run_id": run_id,
                    "incident_id": sim_incident_id,
                    "source_fixture_incident_id": declared,
                    "simulation": True,
                    "fixture_upload_name": upload_name,
                    "payload": pl,
                    "report": report,
                    "subsystem": str(result.get("subsystem") or ""),
                    "risk": str(result.get("risk") or ""),
                    "escalated": bool(result.get("escalated")),
                    "trace_id": str(result.get("trace_id") or ""),
                    "stage_timings": result.get("stage_timings") or [],
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        return JSONResponse(
            status_code=200,
            content={
                "status": "completed",
                "simulation": True,
                "run_key": run_file.stem,
                "run_id": run_id,
                "incident_id": sim_incident_id,
                "source_fixture_incident_id": declared,
                "payload": pl,
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
                    "incident_id": sim_incident_id,
                    "source_fixture_incident_id": declared,
                    "simulation": True,
                    "fixture_upload_name": upload_name,
                    "payload": pl,
                    "error": str(e),
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}") from e


@app.post("/runs/simulate/quick")
def simulate_run_quick(form: SimulateQuickFormPayload) -> JSONResponse:
    """
    PS2.7: prosty formularz — walidacja Pydantic; backend składa `payload` i uruchamia symulację.
    """
    pl = form.build_payload()
    return _simulate_run_core(form.declared_incident_id, pl, "quick-form.json")


@app.post("/runs/simulate")
async def simulate_run_from_fixture(
    file: UploadFile = File(
        ..., description="Single UTF-8 JSON object: incident_id + payload"
    ),
) -> JSONResponse:
    """
    PS2.7: upload a small incident-shaped JSON fixture and run the pipeline under an isolated
    incident_id (sim-upload-…). Same persistence shape as POST /runs; list rows set simulation=true.
    """
    raw = await file.read()
    if len(raw) > FIXTURE_UPLOAD_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Fixture too large (max {FIXTURE_UPLOAD_MAX_BYTES} bytes)",
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400, detail="Fixture must be valid UTF-8 text"
        ) from exc
    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty fixture")
    try:
        obj: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise HTTPException(
            status_code=400, detail="Fixture must be a single JSON object"
        )
    declared = str(obj.get("incident_id") or "").strip()
    pl = obj.get("payload")
    if not declared:
        raise HTTPException(
            status_code=400,
            detail="Fixture must include non-empty string incident_id",
        )
    if not isinstance(pl, dict):
        raise HTTPException(
            status_code=400,
            detail="Fixture must include payload as a JSON object",
        )

    return _simulate_run_core(declared, pl, file.filename or "fixture.json")


_RUN_KEY_SAFE = re.compile(r"^run_[A-Za-z0-9._-]+$")


def _report_summary(report: Any) -> str | None:
    if not isinstance(report, dict):
        return None
    return report.get("summary") or report.get("executive_summary")


def _derive_confidence(pl: dict[str, Any], escalated: bool | None, report: Any) -> str:
    c = pl.get("confidence")
    if isinstance(c, str) and c.strip():
        return c.strip().lower()
    if escalated is True:
        return "low"
    if isinstance(report, dict):
        refs = report.get("citation_refs") or []
        if isinstance(refs, list) and len(refs) > 0:
            return "high"
    return "medium"


def _run_row_from_file(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    report = payload.get("report")
    error = payload.get("error")
    pl = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    raw_esc = payload.get("escalated")
    if isinstance(raw_esc, bool):
        esc_out: bool = raw_esc
    else:
        esc_out = False
        if isinstance(report, dict) and report.get("escalation_packet"):
            esc_out = True
        elif isinstance(report, dict):
            es = str(report.get("executive_summary") or "")
            if es.startswith("[ESCALATION]"):
                esc_out = True
    created_at = datetime.fromtimestamp(
        path.stat().st_mtime, tz=timezone.utc
    ).isoformat()
    summary = _report_summary(report)
    sat_id = pl.get("sat_id") if isinstance(pl.get("sat_id"), str) else None
    if sat_id is None and isinstance(pl.get("satellite_id"), str):
        sat_id = pl.get("satellite_id")
    trace_id = str(payload.get("trace_id") or "").strip()
    trace_link: str | None = None
    if isinstance(report, dict):
        tl = report.get("trace_link")
        if isinstance(tl, str) and tl.strip():
            trace_link = tl.strip()
    return {
        "id": path.stem,
        "run_id": payload.get("run_id", path.stem),
        "incident_id": payload.get("incident_id", ""),
        "status": "completed" if error is None else "error",
        "created_at": created_at,
        "summary": summary,
        "error": error,
        "subsystem": str(payload.get("subsystem") or ""),
        "risk": str(payload.get("risk") or ""),
        "escalated": esc_out,
        "sat_id": sat_id or "",
        "confidence": _derive_confidence(pl, esc_out, report),
        "trace_id": trace_id or None,
        "trace_link": trace_link,
        "simulation": bool(payload.get("simulation")),
    }


@app.get("/runs")
def list_runs(
    limit: int = Query(20, ge=1, le=200),
    subsystem: str | None = Query(
        None, description="Filter: subsystem equals (case-insensitive)"
    ),
    risk: str | None = Query(
        None, description="Filter: risk equals (case-insensitive)"
    ),
    escalated: bool | None = Query(None, description="Filter by escalation flag"),
    status: str | None = Query(None, description="completed or error"),
    sat_id: str | None = Query(
        None, description="Substring match on sat_id from payload"
    ),
    confidence: str | None = Query(
        None, description="low | medium | high (derived unless payload sets confidence)"
    ),
    after: str | None = Query(
        None, description="ISO8601: include runs with created_at >= after"
    ),
    before: str | None = Query(
        None, description="ISO8601: include runs with created_at <= before"
    ),
    simulation: bool | None = Query(
        None,
        description="When true/false, filter rows from POST /runs/simulate (PS2.7)",
    ),
) -> JSONResponse:
    """
    List recent incident runs persisted by POST /runs (PS2.1: filters for operator UI).

    Returns metadata including subsystem, risk, escalated, sat_id, confidence when inferable.
    """
    runs_dir = DATA_DIR / "incidents"
    if not runs_dir.exists():
        return JSONResponse(status_code=200, content={"runs": []})

    files = sorted(
        runs_dir.glob("run_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    after_dt = None
    before_dt = None
    if after:
        try:
            after_dt = datetime.fromisoformat(after.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=422, detail="Invalid after datetime (use ISO8601)"
            )
    if before:
        try:
            before_dt = datetime.fromisoformat(before.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=422, detail="Invalid before datetime (use ISO8601)"
            )

    sub_f = (subsystem or "").strip().lower() or None
    risk_f = (risk or "").strip().lower() or None
    conf_f = (confidence or "").strip().lower() or None
    sat_f = (sat_id or "").strip().lower() or None
    status_f = (status or "").strip().lower() or None
    if status_f and status_f not in ("completed", "error"):
        raise HTTPException(
            status_code=422, detail="status must be 'completed' or 'error' when set"
        )
    if conf_f and conf_f not in ("low", "medium", "high"):
        raise HTTPException(
            status_code=422, detail="confidence must be low, medium, or high when set"
        )

    out: list[dict[str, Any]] = []
    scanned = 0
    max_scan = 500
    for path in files:
        if scanned >= max_scan:
            break
        scanned += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        row = _run_row_from_file(path, payload)
        if after_dt:
            try:
                ca = datetime.fromisoformat(
                    str(row["created_at"]).replace("Z", "+00:00")
                )
            except ValueError:
                continue
            if ca < after_dt:
                continue
        if before_dt:
            try:
                cb = datetime.fromisoformat(
                    str(row["created_at"]).replace("Z", "+00:00")
                )
            except ValueError:
                continue
            if cb > before_dt:
                continue
        if sub_f and str(row.get("subsystem") or "").lower() != sub_f:
            continue
        if risk_f and str(row.get("risk") or "").lower() != risk_f:
            continue
        if escalated is not None and bool(row.get("escalated")) != escalated:
            continue
        if status_f and str(row.get("status") or "").lower() != status_f:
            continue
        if sat_f and sat_f not in str(row.get("sat_id") or "").lower():
            continue
        if conf_f and str(row.get("confidence") or "").lower() != conf_f:
            continue
        if simulation is not None and bool(row.get("simulation")) != simulation:
            continue
        out.append(row)
        if len(out) >= limit:
            break

    return JSONResponse(status_code=200, content={"runs": out})


@app.get("/runs/{run_key}")
def get_run(run_key: str) -> JSONResponse:
    """Return one persisted run JSON by file stem (id from GET /runs)."""
    if not _RUN_KEY_SAFE.match(run_key) or len(run_key) > 240:
        raise HTTPException(status_code=400, detail="Invalid run_key")
    runs_dir = DATA_DIR / "incidents"
    path = runs_dir / f"{run_key}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Run not found")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Invalid run file: {exc}") from exc
    return JSONResponse(status_code=200, content=payload)


@app.get("/replays/{run_id}")
def get_replay_metadata(run_id: str) -> JSONResponse:
    """PS1.4: Retrieve persisted replay metadata by run_id."""
    from apps.replay.metadata import load_replay_metadata

    try:
        metadata = load_replay_metadata(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return JSONResponse(status_code=200, content={"replay": metadata})


@app.post("/replays/{run_id}/run")
def replay_run(run_id: str) -> JSONResponse:
    """PS1.5: Replay a stored run input and compare key outcomes."""
    from apps.replay.workflow import replay_by_run_id

    try:
        result = replay_by_run_id(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return JSONResponse(status_code=200, content=result)


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
