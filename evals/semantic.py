"""
PS4.4 — Deterministic semantic evals against fixture pipeline results (no LLM).

Scores citation precision, audit semantics (no_evidence, tool_failure, policy_deny),
and empty-vs-failure distinction using the same rubric as live evals (score_case).

Run from repo root:
  python -m evals.semantic
  python -m evals.semantic --write-summary data/eval-reports/semantic-latest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.scoring import score_case  # noqa: E402

SEMANTIC_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = SEMANTIC_DIR / "fixtures" / "semantic"
CASES_PATH = SEMANTIC_DIR / "semantic_cases.yaml"


def load_semantic_cases() -> list[dict]:
    import yaml

    data = yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))
    return data.get("cases") or []


def load_fixture(name: str) -> dict[str, Any]:
    path = FIXTURES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"semantic fixture not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_semantic_suite(
    *,
    write_summary: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    """
    Run all semantic cases. Returns (exit_code, summary_dict).
    """
    cases = load_semantic_cases()
    if not cases:
        print("No cases in evals/semantic_cases.yaml")
        return 1, {"cases": [], "passed": 0, "failed": 0}

    rows: list[dict[str, Any]] = []
    failed_count = 0

    print("--- Semantic eval suite (PS4.4, no LLM) ---")
    for case in cases:
        case_id = str(case.get("id") or "?")
        fixture_name = str(case.get("fixture") or "")
        expect_pass = case.get("expect_scoring_pass", True) is not False

        try:
            result = load_fixture(fixture_name)
        except Exception as exc:
            print(f"  FAIL  {case_id}  fixture_error: {exc}")
            failed_count += 1
            rows.append(
                {
                    "case_id": case_id,
                    "passed": False,
                    "expect_scoring_pass": expect_pass,
                    "failures": [str(exc)],
                    "triage_gate": case.get("triage_gate"),
                }
            )
            continue

        scoring_passed, failures = score_case(case, result)
        case_ok = scoring_passed == expect_pass
        if case_ok:
            print(f"  PASS  {case_id}")
        else:
            print(
                f"  FAIL  {case_id}  scoring_passed={scoring_passed} "
                f"expect_scoring_pass={expect_pass}  {'; '.join(failures)}"
            )
            failed_count += 1

        rows.append(
            {
                "case_id": case_id,
                "passed": case_ok,
                "scoring_passed": scoring_passed,
                "expect_scoring_pass": expect_pass,
                "failures": failures,
                "triage_gate": case.get("triage_gate"),
                "fixture": fixture_name,
            }
        )

    passed_count = len(cases) - failed_count
    summary = {
        "suite": "semantic_ps44",
        "total": len(cases),
        "passed": passed_count,
        "failed": failed_count,
        "cases": rows,
    }
    print(f"\nSemantic evals: {passed_count}/{len(cases)} passed")
    if failed_count:
        print("Semantic suite: FAIL")
    else:
        print("Semantic suite: PASS")

    if write_summary:
        write_summary.parent.mkdir(parents=True, exist_ok=True)
        write_summary.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote summary: {write_summary}")

    return (0 if failed_count == 0 else 1), summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="PS4.4 semantic eval suite (fixtures)."
    )
    parser.add_argument(
        "--write-summary",
        type=Path,
        default=None,
        help="Write JSON summary with per-case pass/fail details.",
    )
    args = parser.parse_args(argv)
    code, _ = run_semantic_suite(write_summary=args.write_summary)
    return code


if __name__ == "__main__":
    sys.exit(main())
