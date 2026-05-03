from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.agent.graph import run_pipeline
from apps.replay.metadata import load_replay_metadata, replay_payload_fingerprint

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUN_ARTIFACTS_DIR = REPO_ROOT / "data" / "incidents"


def _find_run_artifact(run_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    if not RUN_ARTIFACTS_DIR.exists():
        raise FileNotFoundError("Run artifacts directory does not exist")
    run_paths = sorted(RUN_ARTIFACTS_DIR.glob("run_*.json"), reverse=True)
    incident_paths = sorted(RUN_ARTIFACTS_DIR.glob("incident_*.json"), reverse=True)
    if not run_paths and not incident_paths:
        raise FileNotFoundError(
            f"No run_*.json or incident_*.json under {RUN_ARTIFACTS_DIR}; "
            f"cannot resolve artifact for run_id={run_id}"
        )
    for path in run_paths:
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(artifact.get("run_id") or "").strip() == run_id:
            return artifact
    # Older run files may omit run_id; fixture files use incident_*.json (same payload_hash).
    target_hash = str(metadata.get("payload_hash") or "").strip()
    incident_id = str(metadata.get("incident_id") or "").strip()
    if target_hash and incident_id:
        for path in (*run_paths, *incident_paths):
            try:
                artifact = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if str(artifact.get("incident_id") or "").strip() != incident_id:
                continue
            pl = artifact.get("payload")
            if not isinstance(pl, dict):
                continue
            if replay_payload_fingerprint(pl) == target_hash:
                return artifact
    raise FileNotFoundError(
        f"Run artifact not found for run_id={run_id}: no data/incidents "
        "run_*.json / incident_*.json with matching run_id, or matching incident_id + "
        "payload_hash from replay metadata"
    )


REPLAY_COMPARISON_FIELDS = (
    "subsystem",
    "escalated",
    "has_citations",
    "escalation_reason",
    "citation_count",
)


def _outcome_from_run_artifact(run_artifact: dict[str, Any]) -> dict[str, Any]:
    report = run_artifact.get("report") or {}
    if not isinstance(report, dict):
        report = {}
    packet = report.get("escalation_packet") or {}
    if not isinstance(packet, dict):
        packet = {}
    cites = run_artifact.get("citations") or []
    if not isinstance(cites, list):
        cites = []
    refs = report.get("citation_refs") or []
    if not isinstance(refs, list):
        refs = []
    citation_count = len(cites) if cites else len(refs)
    return {
        "subsystem": str(run_artifact.get("subsystem") or ""),
        "escalated": bool(run_artifact.get("escalated") or bool(packet)),
        "has_citations": bool(cites or refs),
        "escalation_reason": str(packet.get("reason") or ""),
        "citation_count": int(citation_count),
    }


def _extract_outcome_from_result(result: dict[str, Any]) -> dict[str, Any]:
    report = result.get("report") or {}
    if not isinstance(report, dict):
        report = {}
    top_packet = result.get("escalation_packet") or {}
    if not isinstance(top_packet, dict):
        top_packet = {}
    rep_packet = report.get("escalation_packet") or {}
    if not isinstance(rep_packet, dict):
        rep_packet = {}
    reason = str(top_packet.get("reason") or rep_packet.get("reason") or "")
    cites = result.get("citations") or []
    if not isinstance(cites, list):
        cites = []
    refs = report.get("citation_refs") or []
    if not isinstance(refs, list):
        refs = []
    citation_count = len(cites) if cites else len(refs)
    return {
        "subsystem": str(result.get("subsystem") or ""),
        "escalated": bool(result.get("escalated")),
        "has_citations": bool(cites or refs),
        "escalation_reason": reason,
        "citation_count": int(citation_count),
    }


def _extract_original_outcome(
    metadata: dict[str, Any], run_artifact: dict[str, Any]
) -> dict[str, Any]:
    base = _outcome_from_run_artifact(run_artifact)
    original = metadata.get("original_outcome")
    if isinstance(original, dict):
        if "subsystem" in original:
            base["subsystem"] = str(original.get("subsystem") or "")
        if "escalated" in original:
            base["escalated"] = bool(original.get("escalated"))
        if "has_citations" in original:
            base["has_citations"] = bool(original.get("has_citations"))
        if "escalation_reason" in original:
            base["escalation_reason"] = str(original.get("escalation_reason") or "")
        if "citation_count" in original:
            try:
                base["citation_count"] = int(original["citation_count"])
            except (TypeError, ValueError):
                base["citation_count"] = 0
    return base


def compare_outcomes(
    original: dict[str, Any], replay: dict[str, Any]
) -> dict[str, Any]:
    fields = REPLAY_COMPARISON_FIELDS
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
    run_artifact = _find_run_artifact(run_id, metadata)

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
