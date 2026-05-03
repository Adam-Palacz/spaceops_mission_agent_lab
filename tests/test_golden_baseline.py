from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.replay.golden import (
    baseline_path_for_run,
    check_manifest,
    check_run_against_baseline,
    load_baseline,
    load_manifest,
)
from apps.replay.workflow import replay_by_run_id

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "golden"


def _patch_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "apps.replay.metadata.REPLAY_RUNS_DIR",
        FIXTURE_ROOT / "replay_runs",
    )
    monkeypatch.setattr(
        "apps.replay.workflow.RUN_ARTIFACTS_DIR",
        FIXTURE_ROOT / "incidents",
    )


def test_manifest_and_fixture_paths_resolve() -> None:
    manifest = load_manifest(FIXTURE_ROOT / "manifest.json")
    assert manifest["cases"][0]["run_id"] == "r-golden-ci"
    bp = baseline_path_for_run(FIXTURE_ROOT / "baselines", "r-golden-ci")
    assert bp.name == "run_r-golden-ci_baseline.json"
    load_baseline(bp)


def test_golden_ci_matches_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_paths(monkeypatch)

    monkeypatch.setattr(
        "apps.replay.workflow.run_pipeline",
        lambda **_kwargs: {
            "run_id": "replay-ci",
            "subsystem": "Power",
            "escalated": False,
            "citations": [{"doc_id": "rb"}],
            "report": {"citation_refs": ["rb"]},
        },
    )

    ok, failures = check_manifest(
        FIXTURE_ROOT / "manifest.json",
        FIXTURE_ROOT / "baselines",
        replay_fn=replay_by_run_id,
    )
    assert ok is True
    assert failures == []


def test_golden_ci_detects_regression(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_paths(monkeypatch)

    monkeypatch.setattr(
        "apps.replay.workflow.run_pipeline",
        lambda **_kwargs: {
            "run_id": "replay-ci-bad",
            "subsystem": "Thermal",
            "escalated": False,
            "citations": [{"doc_id": "rb"}],
            "report": {"citation_refs": ["rb"]},
        },
    )

    ok, failures = check_manifest(
        FIXTURE_ROOT / "manifest.json",
        FIXTURE_ROOT / "baselines",
        replay_fn=replay_by_run_id,
    )
    assert ok is False
    assert failures and failures[0]["diffs"]


def test_load_baseline_rejects_unknown_field(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps(
            {
                "schema_version": "golden_baseline_v1",
                "run_id": "x",
                "expected_outcome": {"subsystem": "Power", "extra_bad": 1},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown field"):
        load_baseline(bad)


def test_check_run_run_id_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "m.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "golden_baseline_v1",
                "run_id": "other-id",
                "expected_outcome": {"subsystem": "Power"},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="run_id mismatch"):
        check_run_against_baseline(
            "expected-run-id",
            path,
            replay_fn=lambda _rid: {"comparison": {"replay": {"subsystem": "Power"}}},
        )
