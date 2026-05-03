"""Golden-run baselines (PS2.8): approved replay outcomes pinned for regression checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from apps.replay.workflow import REPLAY_COMPARISON_FIELDS, replay_by_run_id

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_DIR = REPO_ROOT / "data" / "replay" / "golden"
GOLDEN_MANIFEST_PATH = GOLDEN_DIR / "manifest.json"
GOLDEN_BASELINES_DIR = GOLDEN_DIR / "baselines"

BASELINE_SCHEMA_VERSION = "golden_baseline_v1"
MANIFEST_SCHEMA_VERSION = "golden_manifest_v1"


def baseline_path_for_run(baselines_dir: Path, run_id: str) -> Path:
    safe = run_id.replace("/", "").replace("\\", "")
    return baselines_dir / f"run_{safe}_baseline.json"


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    ver = data.get("schema_version")
    if ver != MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"Golden manifest {path}: expected schema_version={MANIFEST_SCHEMA_VERSION!r}, got {ver!r}"
        )
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError(f"Golden manifest {path}: missing or invalid 'cases' list")
    return data


def load_baseline(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != BASELINE_SCHEMA_VERSION:
        raise ValueError(
            f"Baseline {path}: expected schema_version={BASELINE_SCHEMA_VERSION!r}, "
            f"got {data.get('schema_version')!r}"
        )
    expected = data.get("expected_outcome")
    if not isinstance(expected, dict) or not expected:
        raise ValueError(f"Baseline {path}: missing or empty expected_outcome")
    for key in expected:
        if key not in REPLAY_COMPARISON_FIELDS:
            raise ValueError(
                f"Baseline {path}: unknown field {key!r} in expected_outcome "
                f"(allowed: {REPLAY_COMPARISON_FIELDS})"
            )
    return data


def diff_expected_vs_replay(
    expected: dict[str, Any], replay_outcome: dict[str, Any]
) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    for field in expected:
        ev = expected[field]
        rv = replay_outcome.get(field)
        if ev != rv:
            diffs.append({"field": field, "baseline": ev, "replay": rv})
    return diffs


def check_run_against_baseline(
    run_id: str,
    baseline_file: Path,
    *,
    replay_fn: Callable[[str], dict[str, Any]] = replay_by_run_id,
) -> tuple[bool, dict[str, Any]]:
    baseline_doc = load_baseline(baseline_file)
    rid = str(baseline_doc.get("run_id") or "").strip()
    if rid and rid != run_id:
        raise ValueError(
            f"Baseline run_id mismatch: manifest says {run_id!r}, file has {rid!r}"
        )
    result = replay_fn(run_id)
    comparison = result.get("comparison") or {}
    replay_outcome = comparison.get("replay") or {}
    expected = baseline_doc["expected_outcome"]
    diffs = diff_expected_vs_replay(expected, replay_outcome)
    return (
        len(diffs) == 0,
        {
            "run_id": run_id,
            "diffs": diffs,
            "replay_outcome": replay_outcome,
        },
    )


def check_manifest(
    manifest_path: Path,
    baselines_dir: Path,
    *,
    replay_fn: Callable[[str], dict[str, Any]] = replay_by_run_id,
) -> tuple[bool, list[dict[str, Any]]]:
    manifest = load_manifest(manifest_path)
    all_diffs: list[dict[str, Any]] = []
    ok = True
    for raw in manifest["cases"]:
        if not isinstance(raw, dict):
            raise ValueError("Manifest case entry must be an object")
        run_id = str(raw.get("run_id") or "").strip()
        if not run_id:
            raise ValueError("Manifest case missing run_id")
        bpath = baseline_path_for_run(baselines_dir, run_id)
        if not bpath.is_file():
            raise FileNotFoundError(
                f"Missing baseline file for run_id={run_id}: {bpath}"
            )
        passed, detail = check_run_against_baseline(run_id, bpath, replay_fn=replay_fn)
        if not passed:
            ok = False
            all_diffs.append(detail)
    return ok, all_diffs
