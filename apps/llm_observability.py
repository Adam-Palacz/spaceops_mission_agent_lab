"""
LLM observability spine (S3.0) — lightweight, Langfuse-compatible in spirit.

Provides a small API for recording LLM runs and calls with metadata such as
run_id, node, model_id, prompt_id, prompt_version, and optional eval tags.
Uses existing tooling only: append-only NDJSON under data/llm_runs/ and
optional OTel span attributes when tracing is enabled.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opentelemetry import trace

REPO_ROOT = Path(__file__).resolve().parent.parent
LLM_RUNS_DIR = REPO_ROOT / "data" / "llm_runs"
LLM_RUNS_FILE = LLM_RUNS_DIR / "runs.ndjson"
LLM_CALLS_FILE = LLM_RUNS_DIR / "llm_calls.ndjson"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_write(path: Path, record: dict[str, Any]) -> None:
    """
    Append one JSON line to path. Best-effort: never raises to callers.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
            f.write("\n")
    except Exception:
        # Observability must not break agent behaviour.
        return


def start_llm_run(run_id: str | None = None, **metadata: Any) -> str:
    """
    Ensure there is a logical run_id for grouping LLM calls.

    - If run_id is provided, reuse it.
    - Otherwise, generate a new UUID4-based id.
    - Append a record to runs.ndjson (best-effort).
    """
    rid = (run_id or "").strip() or uuid.uuid4().hex
    record: dict[str, Any] = {
        "timestamp": _now_iso(),
        "run_id": rid,
    }
    if metadata:
        record["metadata"] = metadata
    _safe_write(LLM_RUNS_FILE, record)
    return rid


def log_llm_call(
    run_id: str,
    *,
    node: str,
    model_id: str,
    prompt_id: str,
    prompt_version: str | None = None,
    tags: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    eval_case_id: str | None = None,
    injection_case_id: str | None = None,
) -> None:
    """
    Record one LLM call in the observability spine and annotate current span.

    Best-effort: failures are swallowed so they never affect agent logic.
    """
    try:
        record: dict[str, Any] = {
            "timestamp": _now_iso(),
            "run_id": run_id,
            "node": node,
            "model_id": model_id,
            "prompt_id": prompt_id,
        }
        if prompt_version:
            record["prompt_version"] = prompt_version
        if tags:
            record["tags"] = tags
        if metrics:
            record["metrics"] = metrics
        if eval_case_id:
            record["eval_case_id"] = eval_case_id
        if injection_case_id:
            record["injection_case_id"] = injection_case_id
        _safe_write(LLM_CALLS_FILE, record)
    except Exception:
        # File write errors are ignored; still try span attributes below.
        pass

    # Attach attributes to current OTel span if tracing is active.
    try:
        span = trace.get_current_span()
        if span and span.is_recording():
            span.set_attribute("llm.run_id", run_id)
            span.set_attribute("llm.node", node)
            span.set_attribute("llm.model_id", model_id)
            span.set_attribute("llm.prompt_id", prompt_id)
            if prompt_version:
                span.set_attribute("llm.prompt_version", prompt_version)
            if eval_case_id:
                span.set_attribute("llm.eval_case_id", eval_case_id)
            if injection_case_id:
                span.set_attribute("llm.injection_case_id", injection_case_id)
    except Exception:
        return
