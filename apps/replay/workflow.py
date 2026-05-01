from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.agent.graph import run_pipeline
from apps.replay.metadata import load_replay_metadata

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUN_ARTIFACTS_DIR = REPO_ROOT / "data" / "incidents"


def _find_run_artifact(run_id: str) -> dict[str, Any]:
    if not RUN_ARTIFACTS_DIR.exists():
        raise FileNotFoundError("Run artifacts directory does not exist")
    for path in sorted(RUN_ARTIFACTS_DIR.glob("run_*.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(payload.get("run_id") or "").strip() == run_id:
            return payload
    raise FileNotFoundError(f"Run artifact not found for run_id={run_id}")


def _extract_outcome_from_result(result: dict[str, Any]) -> dict[str, Any]:
    report = result.get("report") or {}
    return {
        "subsystem": str(result.get("subsystem") or ""),
        "escalated": bool(result.get("escalated")),
        "has_citations": bool(
            (result.get("citations") or []) or (report.get("citation_refs") or [])
        ),
    }


def _extract_original_outcome(
    metadata: dict[str, Any], run_artifact: dict[str, Any]
) -> dict[str, Any]:
    original = metadata.get("original_outcome")
    if isinstance(original, dict):
        return {
            "subsystem": str(original.get("subsystem") or ""),
            "escalated": bool(original.get("escalated")),
            "has_citations": bool(original.get("has_citations")),
        }
    report = run_artifact.get("report") or {}
    return {
        "subsystem": str(run_artifact.get("subsystem") or ""),
        "escalated": bool(
            run_artifact.get("escalated") or bool(report.get("escalation_packet"))
        ),
        "has_citations": bool(report.get("citation_refs") or []),
    }


def compare_outcomes(
    original: dict[str, Any], replay: dict[str, Any]
) -> dict[str, Any]:
    fields = ("subsystem", "escalated", "has_citations")
    diffs: list[dict[str, Any]] = []
    for field in fields:
        old = original.get(field)
        new = replay.get(field)
        if old != new:
            diffs.append({"field": field, "original": old, "replay": new})
    return {
        "original": original,
        "replay": replay,
        "has_diff": bool(diffs),
        "diffs": diffs,
    }


def replay_by_run_id(run_id: str) -> dict[str, Any]:
    metadata = load_replay_metadata(run_id)
    run_artifact = _find_run_artifact(run_id)

    payload = run_artifact.get("payload")
    if not isinstance(payload, dict):
        raise ValueError(
            f"Run artifact for run_id={run_id} does not contain replayable payload"
        )
    incident_id = str(
        metadata.get("incident_id") or run_artifact.get("incident_id") or ""
    )
    if not incident_id:
        raise ValueError(f"Replay metadata for run_id={run_id} is missing incident_id")

    replay_result = run_pipeline(
        incident_id=incident_id,
        payload=payload,
        replay_source="replay_api",
    )
    original_outcome = _extract_original_outcome(metadata, run_artifact)
    replay_outcome = _extract_outcome_from_result(replay_result)
    comparison = compare_outcomes(original_outcome, replay_outcome)
    return {
        "run_id": run_id,
        "replay_run_id": replay_result.get("run_id"),
        "incident_id": incident_id,
        "comparison": comparison,
        "metadata": metadata,
    }
