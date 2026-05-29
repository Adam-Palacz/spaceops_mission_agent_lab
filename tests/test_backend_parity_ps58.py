"""
PS5.8 — Backend parity eval suite unit tests (fixture-based, no live LLM).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.backend_parity import (
    COMPARABLE_STATUS,
    ParityRunnerError,
    build_case_arm,
    derive_parity_status,
    merge_parity_report,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "backend_parity"
SAMPLE_REPORT = (
    Path(__file__).resolve().parent.parent
    / "evals"
    / "reports"
    / "sample_backend_parity_report.json"
)


def _call(
    *,
    call_index: int,
    node: str,
    backend_requested: str,
    backend_actual: str,
    fallback_used: bool = False,
    fallback_reason: str = "",
) -> dict:
    return {
        "call_index": call_index,
        "node": node,
        "backend_requested": backend_requested,
        "backend_actual": backend_actual,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
    }


def test_single_call_fallback_all_openai_is_invalid_fallback_not_mixed():
    provenance = [
        _call(
            call_index=0,
            node="triage",
            backend_requested="gpu",
            backend_actual="openai",
            fallback_used=True,
            fallback_reason="gpu_unavailable",
        )
    ]
    assert derive_parity_status("gpu", provenance) == "invalid_fallback"


def test_mixed_run_gpu_then_openai_fallback_is_invalid_mixed_backends_priority():
    provenance = [
        _call(
            call_index=0,
            node="triage",
            backend_requested="gpu",
            backend_actual="gpu",
        ),
        _call(
            call_index=1,
            node="decide",
            backend_requested="gpu",
            backend_actual="openai",
            fallback_used=True,
            fallback_reason="gpu_error",
        ),
    ]
    assert derive_parity_status("gpu", provenance) == "invalid_mixed_backends"


def test_openai_baseline_cursor_sh_mismatch_blocks_promotion_while_gpu_comparable():
    openai_arm = build_case_arm(
        case_id="citation-present",
        backend_arm="openai",
        llm_calls_provenance=[
            _call(
                call_index=0,
                node="triage",
                backend_requested="openai",
                backend_actual="cursor_sh",
            ),
            _call(
                call_index=1,
                node="decide",
                backend_requested="openai",
                backend_actual="cursor_sh",
            ),
        ],
    )
    gpu_arm = build_case_arm(
        case_id="citation-present",
        backend_arm="gpu",
        llm_calls_provenance=[
            _call(
                call_index=0,
                node="triage",
                backend_requested="gpu",
                backend_actual="gpu",
            ),
            _call(
                call_index=1,
                node="decide",
                backend_requested="gpu",
                backend_actual="gpu",
            ),
        ],
    )
    assert openai_arm["parity_status"] == "invalid_backend_mismatch"
    assert gpu_arm["parity_status"] == COMPARABLE_STATUS

    report = merge_parity_report([openai_arm, gpu_arm])
    assert report["gpu_promotion"] == "blocked"
    assert any(
        b["backend_arm"] == "openai"
        and b["parity_status"] == "invalid_backend_mismatch"
        for b in report["promotion_blockers"]
    )
    assert report["comparisons"] == []


def test_missing_required_arm_blocks_promotion():
    gpu_only = build_case_arm(
        case_id="must-escalate-no-evidence",
        backend_arm="gpu",
        llm_calls_provenance=[
            _call(
                call_index=0,
                node="triage",
                backend_requested="gpu",
                backend_actual="gpu",
            ),
        ],
    )
    report = merge_parity_report([gpu_only])
    assert report["gpu_promotion"] == "blocked"
    assert any(
        b["case_id"] == "must-escalate-no-evidence"
        and b["parity_status"] == "missing_arm"
        and b["backend_arm"] == "openai"
        for b in report["promotion_blockers"]
    )


def test_gpu_unavailable_without_fallback_recorded():
    provenance = [
        _call(
            call_index=0,
            node="triage",
            backend_requested="gpu",
            backend_actual="openai",
            fallback_used=False,
            fallback_reason="",
        ),
    ]
    assert derive_parity_status("gpu", provenance) == "invalid_gpu_unavailable"


def test_empty_provenance_raises_parity_runner_error():
    with pytest.raises(ParityRunnerError, match="empty llm_calls_provenance"):
        derive_parity_status("openai", [])


def test_invalid_backend_arm_raises():
    with pytest.raises(ParityRunnerError, match="invalid backend_arm"):
        derive_parity_status(
            "cursor_sh",
            [
                _call(
                    call_index=0,
                    node="triage",
                    backend_requested="openai",
                    backend_actual="openai",
                )
            ],
        )


def test_comparable_when_all_calls_match_backend_arm():
    provenance = [
        _call(
            call_index=0,
            node="triage",
            backend_requested="openai",
            backend_actual="openai",
        ),
        _call(
            call_index=1,
            node="decide",
            backend_requested="openai",
            backend_actual="openai",
        ),
    ]
    arm = build_case_arm(
        case_id="must-escalate-no-evidence",
        backend_arm="openai",
        llm_calls_provenance=provenance,
    )
    assert arm["valid_for_parity"] is True
    assert arm["parity_status"] == COMPARABLE_STATUS


def test_sample_report_schema_and_invalid_status_examples():
    assert (
        SAMPLE_REPORT.exists()
    ), "sample_backend_parity_report.json required for PS5.8"
    report = json.loads(SAMPLE_REPORT.read_text(encoding="utf-8"))
    assert report["schema_version"] == "ps58_v1"
    assert "gpu_promotion" in report
    keys = [(a["case_id"], a["backend_arm"]) for a in report["case_arms"]]
    assert len(keys) == len(set(keys))
    statuses = {a["parity_status"] for a in report["case_arms"]}
    for required in (
        "invalid_fallback",
        "invalid_mixed_backends",
        "invalid_gpu_unavailable",
        "invalid_backend_mismatch",
        COMPARABLE_STATUS,
    ):
        assert required in statuses, f"missing sample parity_status {required!r}"


def test_sample_report_blockers_match_merge_for_required_cases():
    """Sample excluded/promotion sections must match merge_parity_report on required arms."""
    report = json.loads(SAMPLE_REPORT.read_text(encoding="utf-8"))
    required_ids = tuple(report["required_case_ids"])
    required_arms = [a for a in report["case_arms"] if a["case_id"] in required_ids]
    merged = merge_parity_report(required_arms, required_case_ids=required_ids)

    def _blocker_key(row: dict) -> tuple[str, str, str]:
        return (
            str(row["case_id"]),
            str(row["backend_arm"]),
            str(row["parity_status"]),
        )

    assert {_blocker_key(b) for b in report["promotion_blockers"]} == {
        _blocker_key(b) for b in merged["promotion_blockers"]
    }
    assert report["gpu_promotion"] == merged["gpu_promotion"]

    def _excluded_key(row: dict) -> tuple[str, str, str]:
        return (
            str(row["case_id"]),
            str(row["backend_arm"]),
            str(row["parity_status"]),
        )

    sample_excluded = {_excluded_key(e) for e in report["excluded_from_comparison"]}
    merged_excluded = {_excluded_key(e) for e in merged["excluded_from_comparison"]}
    assert sample_excluded == merged_excluded


def test_fixture_invalid_fallback_arm():
    path = FIXTURES / "arm_gpu_invalid_fallback.json"
    arms = json.loads(path.read_text(encoding="utf-8"))
    report = merge_parity_report(arms)
    assert report["gpu_promotion"] == "blocked"
    gpu_rows = [a for a in arms if a["backend_arm"] == "gpu"]
    assert gpu_rows
    assert gpu_rows[0]["parity_status"] == "invalid_fallback"
    assert gpu_rows[0]["valid_for_parity"] is False


def test_valid_pair_produces_comparison():
    openai_arm = build_case_arm(
        case_id="must-escalate-no-evidence",
        backend_arm="openai",
        llm_calls_provenance=[
            _call(
                call_index=0,
                node="triage",
                backend_requested="openai",
                backend_actual="openai",
            ),
        ],
        pipeline_result={"escalated": True, "citations": [], "report": {}},
    )
    gpu_arm = build_case_arm(
        case_id="must-escalate-no-evidence",
        backend_arm="gpu",
        llm_calls_provenance=[
            _call(
                call_index=0,
                node="triage",
                backend_requested="gpu",
                backend_actual="gpu",
            ),
        ],
        pipeline_result={"escalated": True, "citations": [], "report": {}},
    )
    report = merge_parity_report(
        [openai_arm, gpu_arm],
        required_case_ids=("must-escalate-no-evidence",),
    )
    assert report["gpu_promotion"] == "allowed"
    assert len(report["comparisons"]) == 1
    assert report["comparisons"][0]["escalation_match"] is True
