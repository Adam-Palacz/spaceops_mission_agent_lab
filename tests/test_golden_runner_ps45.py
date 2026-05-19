from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.replay.golden_runner import (
    DIFF_REPORT_SCHEMA_VERSION,
    UPDATE_CONFIRM_TOKEN,
    build_diff_report,
    refresh_baseline,
    require_update_confirm,
    run_manifest,
    write_report_artifacts,
)

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "golden"
FIXTURE_REPLAY_OK = json.loads(
    (FIXTURE_ROOT / "replay_outcomes" / "r-golden-ci.json").read_text(encoding="utf-8")
)


def _mock_replay_ok(_run_id: str = "") -> dict:
    return FIXTURE_REPLAY_OK


def _mock_replay_regress(_run_id: str = "") -> dict:
    return {
        "comparison": {
            "replay": {
                "subsystem": "Thermal",
                "escalated": False,
                "has_citations": True,
                "escalation_reason": "",
                "citation_count": 1,
            }
        }
    }


def test_ps45_run_manifest_passes_on_unchanged_baseline():
    code, report = run_manifest(
        FIXTURE_ROOT / "manifest.json",
        FIXTURE_ROOT / "baselines",
        replay_fn=_mock_replay_ok,
    )
    assert code == 0
    assert report["gate_status"] == "pass"
    assert report["summary"]["failed"] == 0


def test_ps45_run_manifest_fails_on_semantic_diff(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "golden_manifest_v1",
                "cases": [{"id": "golden-ci", "run_id": "r-golden-ci"}],
            }
        ),
        encoding="utf-8",
    )
    baselines = FIXTURE_ROOT / "baselines"
    code, report = run_manifest(
        manifest,
        baselines,
        replay_fn=_mock_replay_regress,
    )
    assert code == 2
    assert report["gate_status"] == "fail"
    case = report["cases"][0]
    assert case["status"] == "fail"
    assert case["semantic_diffs"]
    assert case["semantic_diffs"][0]["field"] == "subsystem"


def test_ps45_write_report_artifacts_machine_readable(tmp_path: Path):
    case_results = [
        {
            "case_id": "golden-ci",
            "run_id": "r-golden-ci",
            "status": "fail",
            "semantic_diffs": [
                {"field": "subsystem", "baseline": "Power", "replay": "Thermal"}
            ],
            "expected_outcome": {"subsystem": "Power"},
            "replay_outcome": {"subsystem": "Thermal"},
            "error": "",
        }
    ]
    report = build_diff_report(FIXTURE_ROOT / "manifest.json", case_results)
    path = write_report_artifacts(report, tmp_path)
    assert path.name == "report.json"
    assert (tmp_path / "cases" / "golden-ci_diff.json").is_file()
    diff_doc = json.loads(
        (tmp_path / "cases" / "golden-ci_diff.json").read_text(encoding="utf-8")
    )
    assert diff_doc["semantic_diffs"][0]["field"] == "subsystem"
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == DIFF_REPORT_SCHEMA_VERSION


def test_ps45_refresh_baseline_reproducible(tmp_path: Path):
    path = refresh_baseline(
        "run-ps45",
        tmp_path,
        case_id="ps45",
        notes="test",
        replay_fn=_mock_replay_ok,
    )
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["expected_outcome"]["subsystem"] == "Power"
    path2 = refresh_baseline(
        "run-ps45",
        tmp_path,
        replay_fn=_mock_replay_ok,
    )
    assert path2.read_text(encoding="utf-8") == path.read_text(encoding="utf-8")


def test_ps45_fixture_manifest_runs_without_live_replay():
    """make golden-run / replay_fixture path — no pipeline or MCP."""
    code, report = run_manifest(
        FIXTURE_ROOT / "manifest.json",
        FIXTURE_ROOT / "baselines",
    )
    assert code == 0
    assert report["gate_status"] == "pass"


def test_ps45_update_requires_confirm_token():
    with pytest.raises(ValueError, match=UPDATE_CONFIRM_TOKEN):
        require_update_confirm(None)
    require_update_confirm(UPDATE_CONFIRM_TOKEN)
