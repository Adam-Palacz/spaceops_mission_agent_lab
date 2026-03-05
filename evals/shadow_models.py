"""
S3.1 — Model upgrade / shadow-testing pipeline.

Runs a subset of evals against the current production model and one or more
candidate models configured in `config.settings`, then writes a comparison
report under evals/reports/.

Usage (from repo root):

    python -m evals.shadow_models

Requires OPENAI_API_KEY and agent_model_id / agent_candidate_model_ids to be
set appropriately in .env or the environment.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import settings
from evals.scoring import (
    load_cases,
    load_injection_cases,
    run_case,
    run_injection_case,
    score_case,
    unsafe_action_performed,
)
from apps.model_selection import get_current_model_id, get_candidate_model_ids

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "evals" / "reports"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_standard_cases(model_id: str) -> dict[str, Any]:
    """
    Run all standard eval cases using the given model_id as the current agent model.
    """
    # Temporarily override settings.agent_model_id for this run.
    original_model = settings.agent_model_id
    settings.agent_model_id = model_id
    try:
        cases = load_cases()
        summary: list[dict[str, Any]] = []
        passed_count = 0
        for case in cases:
            case_id = case.get("id") or "?"
            try:
                result = run_case(case)
                passed, failures = score_case(case, result)
            except Exception as exc:  # pragma: no cover - smoke path
                passed = False
                failures = [str(exc)]
            if passed:
                passed_count += 1
            summary.append(
                {
                    "id": case_id,
                    "passed": passed,
                    "failures": failures,
                }
            )
        score = passed_count / len(cases) if cases else 0.0
        return {
            "model_id": model_id,
            "total_cases": len(cases),
            "passed": passed_count,
            "score": score,
            "cases": summary,
        }
    finally:
        settings.agent_model_id = original_model


def _run_injection_cases(model_id: str) -> dict[str, Any]:
    """
    Run all injection eval cases using the given model_id as the current agent model.
    """
    original_model = settings.agent_model_id
    settings.agent_model_id = model_id
    try:
        cases = load_injection_cases()
        if not cases:
            return {
                "model_id": model_id,
                "total_cases": 0,
                "unsafe_cases": 0,
                "cases": [],
            }
        summary: list[dict[str, Any]] = []
        unsafe_count = 0
        for case in cases:
            case_id = case.get("id") or "?"
            try:
                result = run_injection_case(case)
                unsafe, reasons = unsafe_action_performed(result)
            except Exception as exc:  # pragma: no cover - smoke path
                unsafe = True
                reasons = [str(exc)]
            if unsafe:
                unsafe_count += 1
            summary.append(
                {
                    "id": case_id,
                    "unsafe": unsafe,
                    "reasons": reasons,
                }
            )
        return {
            "model_id": model_id,
            "total_cases": len(cases),
            "unsafe_cases": unsafe_count,
            "cases": summary,
        }
    finally:
        settings.agent_model_id = original_model


def _write_report(report: dict[str, Any]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = REPORTS_DIR / f"shadow_models_{ts}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return path


def main() -> int:
    if not settings.openai_api_key:
        print(
            "OPENAI_API_KEY is required for shadow-testing; set it in .env or env vars."
        )
        return 1

    current_model = get_current_model_id()
    candidates = get_candidate_model_ids()
    if not candidates:
        print("No candidate models configured (agent_candidate_model_ids is empty).")
        return 1

    print(f"[shadow] Current model: {current_model}")
    print(f"[shadow] Candidate models: {', '.join(candidates)}")

    results: dict[str, Any] = {
        "timestamp": _now_iso(),
        "current_model": current_model,
        "candidates": [],
    }

    # Baseline: current model.
    print(f"[shadow] Running baseline evals for current model: {current_model}")
    current_standard = _run_standard_cases(current_model)
    current_injection = _run_injection_cases(current_model)

    # Candidates.
    for cand in candidates:
        print(f"[shadow] Running evals for candidate model: {cand}")
        cand_standard = _run_standard_cases(cand)
        cand_injection = _run_injection_cases(cand)
        results["candidates"].append(
            {
                "model_id": cand,
                "standard": cand_standard,
                "injection": cand_injection,
            }
        )

    results["baseline"] = {
        "standard": current_standard,
        "injection": current_injection,
    }

    report_path = _write_report(results)
    print(f"[shadow] Report written to {report_path}")

    # Simple pass/fail: any candidate with worse standard score or any unsafe injection cases fails.
    baseline_score = current_standard.get("score", 0.0)
    exit_code = 0
    for cand in results["candidates"]:
        std = cand["standard"]
        inj = cand["injection"]
        if std.get("score", 0.0) < baseline_score or inj.get("unsafe_cases", 0) > 0:
            exit_code = 1
            print(
                f"[shadow] Regression detected for {cand['model_id']}: "
                f"score={std.get('score', 0.0):.2f}, unsafe_cases={inj.get('unsafe_cases', 0)}"
            )

    return exit_code


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())
