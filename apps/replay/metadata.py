"""
Replay metadata persistence (PS1.4).

Stores per-run replay metadata used for deterministic replays, golden runs,
and regression triage.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import settings
from apps.model_selection import get_current_model_id
from prompts.registry import DECIDE_PROMPT_ID, TRIAGE_PROMPT_ID, get_prompt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPLAY_RUNS_DIR = REPO_ROOT / "data" / "replay" / "runs"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _collect_input_refs(payload: dict[str, Any]) -> list[str]:
    refs: set[str] = set()
    candidates = (
        payload.get("event_id"),
        payload.get("input_ref"),
    )
    for item in candidates:
        if isinstance(item, str) and item.strip():
            refs.add(item.strip())
    list_candidates = (
        payload.get("event_ids"),
        payload.get("input_refs"),
        payload.get("telemetry_event_ids"),
    )
    for items in list_candidates:
        if isinstance(items, list):
            for item in items:
                if isinstance(item, str) and item.strip():
                    refs.add(item.strip())
    return sorted(refs)


def build_replay_metadata(
    *,
    run_id: str,
    incident_id: str,
    payload: dict[str, Any],
    trace_id: str,
    status: str,
    replay_source: str,
    llm_calls_used: int,
    original_outcome: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": "v1",
        "captured_at": _now_iso(),
        "run_id": run_id,
        "incident_id": incident_id,
        "status": status,
        "payload_hash": _canonical_hash(payload),
        "input_refs": _collect_input_refs(payload),
        "trace_id": trace_id,
        # Audit trace_id is currently aligned with state trace_id in this project.
        "audit_trace_id": trace_id,
        "replay_source": replay_source,
        "model": {
            "provider": (
                getattr(settings, "llm_provider", "openai") or "openai"
            ).strip(),
            "model_id": get_current_model_id(),
        },
        "prompts": {
            TRIAGE_PROMPT_ID: get_prompt(TRIAGE_PROMPT_ID).version,
            DECIDE_PROMPT_ID: get_prompt(DECIDE_PROMPT_ID).version,
        },
        "runtime": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "llm_calls_used": int(llm_calls_used),
    }
    if original_outcome:
        record["original_outcome"] = original_outcome
    return record


def persist_replay_metadata(metadata: dict[str, Any]) -> Path:
    run_id = str(metadata.get("run_id") or "").strip()
    if not run_id:
        raise ValueError("Missing run_id in replay metadata")
    REPLAY_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPLAY_RUNS_DIR / f"{run_id}.json"
    out.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def load_replay_metadata(run_id: str) -> dict[str, Any]:
    rid = (run_id or "").strip()
    if not rid:
        raise ValueError("run_id must be non-empty")
    path = REPLAY_RUNS_DIR / f"{rid}.json"
    if not path.exists():
        raise FileNotFoundError(f"Replay metadata not found for run_id={rid}")
    data = json.loads(path.read_text(encoding="utf-8"))
    required = (
        "schema_version",
        "run_id",
        "incident_id",
        "payload_hash",
        "trace_id",
        "model",
        "prompts",
        "runtime",
        "replay_source",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(
            f"Replay metadata for run_id={rid} is incomplete; missing keys: {missing}"
        )
    return data
