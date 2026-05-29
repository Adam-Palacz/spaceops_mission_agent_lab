"""
PS5.8 — Backend parity eval suite (openai vs gpu / NIM).

Compares LLM_BACKEND=openai vs LLM_BACKEND=gpu within documented tolerances.
Promotion signal only — does not replace deterministic semantic-evals or evals-hard.

Run from repo root:
  python -m evals.backend_parity --backend openai --write-arm evals/reports/arm_openai.json
  python -m evals.backend_parity --backend gpu --write-arm evals/reports/arm_gpu.json
  python -m evals.backend_parity --merge arm_openai.json arm_gpu.json --write-report report.json
  python -m evals.backend_parity --run-both --write-report evals/reports/backend_parity_latest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.llm_provenance import capture_llm_provenance  # noqa: E402
from config import settings  # noqa: E402
from evals.scoring import load_cases, run_case, score_case  # noqa: E402

REPORTS_DIR = REPO_ROOT / "evals" / "reports"

PARITY_CASE_IDS = ("must-escalate-no-evidence", "citation-present")
VALID_BACKEND_ARMS = frozenset({"openai", "gpu"})
COMPARABLE_STATUS = "comparable"

_REQUIRED_PROVENANCE_KEYS = (
    "call_index",
    "node",
    "backend_requested",
    "backend_actual",
    "fallback_used",
    "fallback_reason",
)


class ParityRunnerError(Exception):
    """Schema/harness fault — do not emit gpu_promotion verdict."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_provenance_call(call: Any, index: int) -> dict[str, Any]:
    if not isinstance(call, dict):
        raise ParityRunnerError(
            f"llm_calls_provenance[{index}] must be a dict, got {type(call).__name__}"
        )
    missing = [k for k in _REQUIRED_PROVENANCE_KEYS if k not in call]
    if missing:
        raise ParityRunnerError(
            f"llm_calls_provenance[{index}] missing fields: {', '.join(missing)}"
        )
    return call


def derive_parity_status(
    backend_arm: str, llm_calls_provenance: list[dict[str, Any]]
) -> str:
    """
    Fixed-priority parity_status derivation (PS5.8 spec).
    Raises ParityRunnerError when provenance is empty or backend_arm is invalid.
    """
    arm = (backend_arm or "").strip().lower()
    if arm not in VALID_BACKEND_ARMS:
        raise ParityRunnerError(f"invalid backend_arm: {backend_arm!r}")
    if not llm_calls_provenance:
        raise ParityRunnerError("empty llm_calls_provenance")

    calls = [
        _validate_provenance_call(c, i) for i, c in enumerate(llm_calls_provenance)
    ]
    actuals = {str(c["backend_actual"]) for c in calls}

    if len(actuals) > 1:
        return "invalid_mixed_backends"
    if any(bool(c.get("fallback_used")) for c in calls):
        return "invalid_fallback"
    if arm == "gpu" and not all(str(c["backend_actual"]) == "gpu" for c in calls):
        return "invalid_gpu_unavailable"
    if arm == "openai" and not all(str(c["backend_actual"]) == "openai" for c in calls):
        return "invalid_backend_mismatch"
    if all(str(c["backend_actual"]) == arm for c in calls):
        return COMPARABLE_STATUS
    raise ParityRunnerError("unhandled parity_status derivation")


def build_case_arm(
    *,
    case_id: str,
    backend_arm: str,
    llm_calls_provenance: list[dict[str, Any]],
    pipeline_result: dict[str, Any] | None = None,
    scoring_failures: list[str] | None = None,
) -> dict[str, Any]:
    """Build one case-arm row with parity_status and valid_for_parity."""
    status = derive_parity_status(backend_arm, llm_calls_provenance)
    row: dict[str, Any] = {
        "case_id": case_id,
        "backend_arm": backend_arm.strip().lower(),
        "llm_calls_provenance": llm_calls_provenance,
        "valid_for_parity": status == COMPARABLE_STATUS,
        "parity_status": status,
    }
    if pipeline_result is not None:
        row["pipeline_result"] = {
            "escalated": bool(pipeline_result.get("escalated")),
            "citations_count": len(pipeline_result.get("citations") or []),
            "citation_refs_count": len(
                (pipeline_result.get("report") or {}).get("citation_refs") or []
            ),
        }
    if scoring_failures is not None:
        row["scoring_failures"] = scoring_failures
    return row


def _offending_call_indices(
    backend_arm: str,
    status: str,
    provenance: list[dict[str, Any]],
) -> list[int]:
    arm = backend_arm.strip().lower()
    if status == "invalid_mixed_backends":
        return [int(c["call_index"]) for c in provenance]
    if status == "invalid_fallback":
        return [
            int(c["call_index"]) for c in provenance if bool(c.get("fallback_used"))
        ]
    if status == "invalid_gpu_unavailable":
        return [
            int(c["call_index"])
            for c in provenance
            if str(c.get("backend_actual")) != "gpu"
        ]
    if status == "invalid_backend_mismatch":
        return [
            int(c["call_index"])
            for c in provenance
            if str(c.get("backend_actual")) != arm
        ]
    return []


def _has_citations(result: dict[str, Any]) -> bool:
    citations = result.get("citations") or []
    refs = (result.get("report") or {}).get("citation_refs") or []
    return len(citations) > 0 or len(refs) > 0


def _max_latency_ms(provenance: list[dict[str, Any]]) -> int | None:
    values = [
        int(c["latency_ms"])
        for c in provenance
        if isinstance(c.get("latency_ms"), (int, float))
    ]
    return max(values) if values else None


def compare_comparable_pair(
    *,
    case_id: str,
    openai_arm: dict[str, Any],
    gpu_arm: dict[str, Any],
    case_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate comparison for a pair where both arms are valid_for_parity."""
    o_res = openai_arm.get("pipeline_result") or {}
    g_res = gpu_arm.get("pipeline_result") or {}
    escalation_match = bool(o_res.get("escalated")) == bool(g_res.get("escalated"))

    o_citations = bool(
        o_res.get("citations_count", 0) or o_res.get("citation_refs_count", 0)
    )
    g_citations = bool(
        g_res.get("citations_count", 0) or g_res.get("citation_refs_count", 0)
    )
    citation_presence_match = o_citations == g_citations

    if (
        case_spec
        and case_spec.get("require_citations")
        and not case_spec.get("must_escalate")
    ):
        citation_presence_match = o_citations and g_citations

    o_prov = openai_arm.get("llm_calls_provenance") or []
    g_prov = gpu_arm.get("llm_calls_provenance") or []
    o_lat = _max_latency_ms(o_prov)
    g_lat = _max_latency_ms(g_prov)
    latency_drift_ms: int | None = None
    if o_lat is not None and g_lat is not None:
        latency_drift_ms = abs(g_lat - o_lat)

    exact_match_fields = ["escalation_yes_no"]
    if case_spec and case_spec.get("require_citations"):
        exact_match_fields.append("citation_present")

    return {
        "case_id": case_id,
        "escalation_match": escalation_match,
        "citation_presence_match": citation_presence_match,
        "openai_latency_ms_max": o_lat,
        "gpu_latency_ms_max": g_lat,
        "latency_drift_ms": latency_drift_ms,
        "latency_within_p95_band": None,
        "exact_match_fields": exact_match_fields,
        "wording_drift_allowed": True,
    }


def merge_parity_report(
    case_arms: list[dict[str, Any]],
    *,
    required_case_ids: tuple[str, ...] = PARITY_CASE_IDS,
    case_specs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Merge openai + gpu arms by case_id; compute promotion verdict and comparisons.
    Raises ParityRunnerError on duplicate (case_id, backend_arm) pairs.
    """
    specs = case_specs or {}
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for arm in case_arms:
        case_id = str(arm.get("case_id") or "").strip()
        backend = str(arm.get("backend_arm") or "").strip().lower()
        if not case_id or backend not in VALID_BACKEND_ARMS:
            raise ParityRunnerError(
                f"invalid case arm row: case_id={case_id!r} backend_arm={backend!r}"
            )
        key = (case_id, backend)
        if key in by_key:
            raise ParityRunnerError(
                f"duplicate case arm: case_id={case_id!r} backend_arm={backend!r}"
            )
        by_key[key] = arm

    promotion_blockers: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for case_id in required_case_ids:
        openai_arm = by_key.get((case_id, "openai"))
        gpu_arm = by_key.get((case_id, "gpu"))

        if openai_arm is None:
            promotion_blockers.append(
                {
                    "case_id": case_id,
                    "backend_arm": "openai",
                    "parity_status": "missing_arm",
                }
            )
        elif not openai_arm.get("valid_for_parity"):
            promotion_blockers.append(
                {
                    "case_id": case_id,
                    "backend_arm": "openai",
                    "parity_status": openai_arm.get("parity_status"),
                }
            )
            excluded.append(
                {
                    "case_id": case_id,
                    "backend_arm": "openai",
                    "parity_status": openai_arm.get("parity_status"),
                    "offending_call_indices": _offending_call_indices(
                        "openai",
                        str(openai_arm.get("parity_status") or ""),
                        openai_arm.get("llm_calls_provenance") or [],
                    ),
                }
            )

        if gpu_arm is None:
            promotion_blockers.append(
                {
                    "case_id": case_id,
                    "backend_arm": "gpu",
                    "parity_status": "missing_arm",
                }
            )
        elif not gpu_arm.get("valid_for_parity"):
            promotion_blockers.append(
                {
                    "case_id": case_id,
                    "backend_arm": "gpu",
                    "parity_status": gpu_arm.get("parity_status"),
                }
            )
            excluded.append(
                {
                    "case_id": case_id,
                    "backend_arm": "gpu",
                    "parity_status": gpu_arm.get("parity_status"),
                    "offending_call_indices": _offending_call_indices(
                        "gpu",
                        str(gpu_arm.get("parity_status") or ""),
                        gpu_arm.get("llm_calls_provenance") or [],
                    ),
                }
            )

        if (
            openai_arm
            and gpu_arm
            and openai_arm.get("valid_for_parity")
            and gpu_arm.get("valid_for_parity")
        ):
            comparisons.append(
                compare_comparable_pair(
                    case_id=case_id,
                    openai_arm=openai_arm,
                    gpu_arm=gpu_arm,
                    case_spec=specs.get(case_id),
                )
            )

    gpu_promotion = "blocked" if promotion_blockers else "allowed"
    return {
        "schema_version": "ps58_v1",
        "timestamp": _now_iso(),
        "tolerance_ref": "docs/evals_backend_parity.md#tolerances",
        "required_case_ids": list(required_case_ids),
        "case_arms": case_arms,
        "comparisons": comparisons,
        "excluded_from_comparison": excluded,
        "gpu_promotion": gpu_promotion,
        "promotion_blockers": promotion_blockers,
    }


def load_parity_case_specs() -> dict[str, dict[str, Any]]:
    """Return eval case specs for PARITY_CASE_IDS."""
    all_cases = {str(c.get("id") or ""): c for c in load_cases()}
    missing = [cid for cid in PARITY_CASE_IDS if cid not in all_cases]
    if missing:
        raise ParityRunnerError(
            f"parity cases missing from evals/cases.yaml: {missing}"
        )
    return {cid: all_cases[cid] for cid in PARITY_CASE_IDS}


def run_backend_arm(
    backend_arm: str,
    *,
    case_ids: tuple[str, ...] = PARITY_CASE_IDS,
) -> list[dict[str, Any]]:
    """Run parity cases under one backend; collect gateway provenance per case arm."""
    arm = backend_arm.strip().lower()
    if arm not in VALID_BACKEND_ARMS:
        raise ParityRunnerError(f"invalid backend_arm: {backend_arm!r}")

    specs = load_parity_case_specs()
    original_backend = settings.llm_backend
    settings.llm_backend = arm
    rows: list[dict[str, Any]] = []
    try:
        for case_id in case_ids:
            case = specs[case_id]
            with capture_llm_provenance() as provenance:
                try:
                    result = run_case(case)
                    _, scoring_failures = score_case(case, result)
                except Exception as exc:
                    raise ParityRunnerError(
                        f"case {case_id!r} failed during backend_arm={arm!r}: {exc}"
                    ) from exc
            rows.append(
                build_case_arm(
                    case_id=case_id,
                    backend_arm=arm,
                    llm_calls_provenance=list(provenance),
                    pipeline_result=result,
                    scoring_failures=scoring_failures,
                )
            )
    finally:
        settings.llm_backend = original_backend
    return rows


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PS5.8 backend parity eval runner.")
    parser.add_argument(
        "--backend",
        choices=sorted(VALID_BACKEND_ARMS),
        help="Run one backend arm and emit case-arm rows.",
    )
    parser.add_argument(
        "--write-arm",
        type=Path,
        default=None,
        help="Write single-arm JSON (list of case_arm rows).",
    )
    parser.add_argument(
        "--merge",
        nargs=2,
        metavar=("ARM_A", "ARM_B"),
        type=Path,
        help="Merge two arm JSON files (each a list of case_arm rows).",
    )
    parser.add_argument(
        "--write-report",
        type=Path,
        default=None,
        help="Write merged parity report JSON.",
    )
    parser.add_argument(
        "--run-both",
        action="store_true",
        help="Run openai and gpu arms sequentially, then merge.",
    )
    parser.add_argument(
        "--soft-signal",
        action="store_true",
        help="Exit 0 even when gpu_promotion=blocked (non-blocking nightly signal).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.run_both:
            arms = run_backend_arm("openai") + run_backend_arm("gpu")
            report = merge_parity_report(arms)
            out = args.write_report or (
                REPORTS_DIR
                / f"backend_parity_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
            )
            _write_json(out, report)
            print(f"[parity] Report written to {out}")
            print(f"[parity] gpu_promotion={report['gpu_promotion']}")
            if report["promotion_blockers"]:
                for b in report["promotion_blockers"]:
                    print(
                        f"  blocker  {b['case_id']}  {b['backend_arm']}  "
                        f"{b['parity_status']}"
                    )
            if report["gpu_promotion"] == "blocked" and not args.soft_signal:
                return 1
            return 0

        if args.backend:
            rows = run_backend_arm(args.backend)
            if args.write_arm:
                _write_json(
                    args.write_arm, {"case_arms": rows, "backend_arm": args.backend}
                )
                print(f"[parity] Arm written to {args.write_arm}")
            else:
                print(json.dumps(rows, indent=2))
            return 0

        if args.merge:
            left = json.loads(args.merge[0].read_text(encoding="utf-8"))
            right = json.loads(args.merge[1].read_text(encoding="utf-8"))
            arms = (left.get("case_arms") if isinstance(left, dict) else left) + (
                right.get("case_arms") if isinstance(right, dict) else right
            )
            report = merge_parity_report(arms)
            out = args.write_report or REPORTS_DIR / "backend_parity_merged.json"
            _write_json(out, report)
            print(f"[parity] Merged report written to {out}")
            print(f"[parity] gpu_promotion={report['gpu_promotion']}")
            if report["gpu_promotion"] == "blocked" and not args.soft_signal:
                return 1
            return 0

        print("Specify --backend, --run-both, or --merge.")
        return 2
    except ParityRunnerError as exc:
        print(f"ParityRunnerError: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
