"""
PS4.5 — Golden runner: execute pinned cases, snapshot semantic outcomes, emit diff reports.

Builds on PS2.8 baselines (`apps.replay.golden`). Compares only REPLAY_COMPARISON_FIELDS
(semantic fields), not full pipeline blobs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from apps.replay.golden import (
    BASELINE_SCHEMA_VERSION,
    baseline_path_for_run,
    diff_expected_vs_replay,
    load_baseline,
    load_manifest,
)
from apps.replay.workflow import REPLAY_COMPARISON_FIELDS, replay_by_run_id

DIFF_REPORT_SCHEMA_VERSION = "golden_diff_report_v1"
UPDATE_CONFIRM_TOKEN = "baseline-update"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _case_id(case: dict[str, Any]) -> str:
    return str(case.get("id") or case.get("case_id") or case.get("run_id") or "unknown")


def _semantic_snapshot(outcome: dict[str, Any]) -> dict[str, Any]:
    """Stable snapshot of compared fields only."""
    return {field: outcome.get(field) for field in REPLAY_COMPARISON_FIELDS}


def _replay_fn_for_case(
    case: dict[str, Any],
    manifest_dir: Path | None,
    default_fn: Callable[[str], dict[str, Any]],
) -> Callable[[str], dict[str, Any]]:
    """Optional replay_fixture JSON beside manifest (deterministic CI / make golden-run)."""
    rel = case.get("replay_fixture")
    if not rel or not manifest_dir:
        return default_fn
    path = manifest_dir / str(rel)
    if not path.is_file():
        return default_fn
    payload = json.loads(path.read_text(encoding="utf-8"))

    def _from_fixture(_run_id: str) -> dict[str, Any]:
        return payload

    return _from_fixture


def run_case(
    case: dict[str, Any],
    baselines_dir: Path,
    *,
    replay_fn: Callable[[str], dict[str, Any]] = replay_by_run_id,
    manifest_dir: Path | None = None,
) -> dict[str, Any]:
    """Run one manifest case; return per-case result (pass/fail/error + semantic diffs)."""
    run_id = str(case.get("run_id") or "").strip()
    cid = _case_id(case)
    if not run_id:
        return {
            "case_id": cid,
            "run_id": "",
            "status": "error",
            "error": "missing run_id",
            "semantic_diffs": [],
        }
    bpath = baseline_path_for_run(baselines_dir, run_id)
    if not bpath.is_file():
        return {
            "case_id": cid,
            "run_id": run_id,
            "status": "error",
            "error": f"missing baseline: {bpath}",
            "semantic_diffs": [],
        }
    try:
        baseline_doc = load_baseline(bpath)
        rid = str(baseline_doc.get("run_id") or "").strip()
        if rid and rid != run_id:
            raise ValueError(
                f"Baseline run_id mismatch: manifest {run_id!r}, file {rid!r}"
            )
        fn = _replay_fn_for_case(case, manifest_dir, replay_fn)
        result = fn(run_id)
        replay_outcome = (result.get("comparison") or {}).get("replay") or {}
        expected = baseline_doc["expected_outcome"]
        semantic_diffs = diff_expected_vs_replay(expected, replay_outcome)
        status = "pass" if not semantic_diffs else "fail"
        return {
            "case_id": cid,
            "run_id": run_id,
            "status": status,
            "baseline_path": str(bpath),
            "semantic_diffs": semantic_diffs,
            "expected_outcome": _semantic_snapshot(expected),
            "replay_outcome": _semantic_snapshot(replay_outcome),
            "error": "",
        }
    except Exception as exc:
        return {
            "case_id": cid,
            "run_id": run_id,
            "status": "error",
            "error": str(exc),
            "semantic_diffs": [],
        }


def build_diff_report(
    manifest_path: Path,
    case_results: list[dict[str, Any]],
) -> dict[str, Any]:
    passed = sum(1 for c in case_results if c.get("status") == "pass")
    failed = sum(1 for c in case_results if c.get("status") == "fail")
    errors = sum(1 for c in case_results if c.get("status") == "error")
    total = len(case_results)
    return {
        "schema_version": DIFF_REPORT_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "manifest": str(manifest_path),
        "comparison_fields": list(REPLAY_COMPARISON_FIELDS),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
        },
        "gate_status": "pass" if failed == 0 and errors == 0 else "fail",
        "cases": case_results,
    }


def run_manifest(
    manifest_path: Path,
    baselines_dir: Path,
    *,
    replay_fn: Callable[[str], dict[str, Any]] = replay_by_run_id,
) -> tuple[int, dict[str, Any]]:
    """
    Execute all manifest cases.

    Returns (exit_code, diff_report). exit_code: 0 pass, 2 mismatch, 1 error.
    """
    manifest = load_manifest(manifest_path)
    results: list[dict[str, Any]] = []
    has_error = False
    has_fail = False
    for raw in manifest["cases"]:
        if not isinstance(raw, dict):
            return 1, {
                "schema_version": DIFF_REPORT_SCHEMA_VERSION,
                "gate_status": "error",
                "error": "invalid manifest case entry",
            }
        detail = run_case(
            raw,
            baselines_dir,
            replay_fn=replay_fn,
            manifest_dir=manifest_path.parent,
        )
        results.append(detail)
        if detail.get("status") == "error":
            has_error = True
        elif detail.get("status") == "fail":
            has_fail = True
    report = build_diff_report(manifest_path, results)
    if has_error:
        return 1, report
    if has_fail:
        return 2, report
    return 0, report


def write_report_artifacts(report: dict[str, Any], output_dir: Path) -> Path:
    """Write machine-readable report.json and per-case diff/snapshot files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cases_dir = output_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    for case in report.get("cases") or []:
        if not isinstance(case, dict):
            continue
        cid = str(case.get("case_id") or "unknown")
        safe = cid.replace("/", "_").replace("\\", "_")
        diff_path = cases_dir / f"{safe}_diff.json"
        snap_path = cases_dir / f"{safe}_snapshot.json"
        diff_doc = {
            "case_id": cid,
            "run_id": case.get("run_id"),
            "status": case.get("status"),
            "semantic_diffs": case.get("semantic_diffs") or [],
            "error": case.get("error") or "",
        }
        diff_path.write_text(
            json.dumps(diff_doc, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        snap_doc = {
            "case_id": cid,
            "run_id": case.get("run_id"),
            "expected_outcome": case.get("expected_outcome") or {},
            "replay_outcome": case.get("replay_outcome") or {},
        }
        snap_path.write_text(
            json.dumps(snap_doc, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        case["diff_artifact"] = str(diff_path.relative_to(output_dir))
        case["snapshot_artifact"] = str(snap_path.relative_to(output_dir))
    report_path = output_dir / "report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report_path


def refresh_baseline(
    run_id: str,
    baselines_dir: Path,
    *,
    case_id: str = "",
    notes: str = "",
    replay_fn: Callable[[str], dict[str, Any]] = replay_by_run_id,
) -> Path:
    """Replay once and write golden_baseline_v1 (operator must confirm via CLI)."""
    result = replay_fn(run_id)
    replay_outcome = (result.get("comparison") or {}).get("replay") or {}
    doc = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "run_id": run_id,
        "case_id": case_id,
        "expected_outcome": _semantic_snapshot(replay_outcome)
        if replay_outcome
        else replay_outcome,
        "notes": notes,
    }
    path = baseline_path_for_run(baselines_dir, run_id)
    baselines_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def require_update_confirm(confirm: str | None) -> None:
    if (confirm or "").strip() != UPDATE_CONFIRM_TOKEN:
        raise ValueError(
            f"Baseline refresh requires --confirm {UPDATE_CONFIRM_TOKEN!r} "
            "(explicit operator intent)."
        )
