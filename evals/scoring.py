"""
S1.11 Evals: run agent per case, compare to expected, compute score.
MoE1 (triage), MoE2 (citations), MoE4 (escalation). Deterministic (temperature=0).
Run from repo root: python -m evals.scoring
Exit 0 if all pass and score >= threshold; else non-zero.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_cases() -> list[dict]:
    """Load evals/cases.yaml."""
    import yaml
    path = Path(__file__).resolve().parent / "cases.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data.get("cases") or []


def run_case(case: dict) -> dict:
    """Run pipeline for one case; return result state."""
    from apps.agent.graph import run_pipeline
    case_id = case.get("id") or "unknown"
    payload = case.get("payload") or {}
    result = run_pipeline(case_id, payload)
    return result


def score_case(case: dict, result: dict) -> tuple[bool, list[str]]:
    """
    Compare result to case expectations. Return (passed, list of failure reasons).
    """
    failures: list[str] = []
    # Triage: subsystem in expected_subsystem (top-k)
    expected_subsystem: list[str] = case.get("expected_subsystem") or []
    if expected_subsystem:
        actual = (result.get("subsystem") or "").strip()
        if actual not in expected_subsystem:
            failures.append(f"triage: expected one of {expected_subsystem}, got '{actual}'")

    # Must escalate
    must_escalate = case.get("must_escalate") is True
    escalated = result.get("escalated") is True
    escalation_packet = result.get("escalation_packet") or {}
    if must_escalate:
        if not escalated:
            failures.append("must_escalate: expected escalation, agent did not escalate")
        elif not escalation_packet.get("reason"):
            failures.append("must_escalate: expected escalation_packet with reason")
    else:
        if escalated and case.get("require_citations"):
            # Require citations but we escalated (no evidence) - fail only if we required citations
            pass  # allow; or fail: failures.append("expected citations but got escalation")
        # If not must_escalate and require_citations, check below

    # Citation presence (when not must_escalate and require_citations)
    if case.get("require_citations") and not must_escalate:
        citations = result.get("citations") or []
        report = result.get("report") or {}
        refs = report.get("citation_refs") or []
        if not escalated and len(citations) == 0 and len(refs) == 0:
            failures.append("require_citations: expected at least one citation or citation_ref")

    passed = len(failures) == 0
    return passed, failures


def main() -> int:
    cases = load_cases()
    if not cases:
        print("No cases in evals/cases.yaml")
        return 1

    threshold = 0.0  # require all pass; could be configurable
    passed_count = 0
    results_summary: list[tuple[str, bool, list[str]]] = []

    for case in cases:
        case_id = case.get("id") or "?"
        try:
            result = run_case(case)
        except Exception as e:
            results_summary.append((case_id, False, [str(e)]))
            continue
        passed, failures = score_case(case, result)
        if passed:
            passed_count += 1
        results_summary.append((case_id, passed, failures))

    # Output
    for case_id, passed, failures in results_summary:
        status = "PASS" if passed else "FAIL"
        print(f"  {status}  {case_id}" + (f"  {'; '.join(failures)}" if failures else ""))
    score = passed_count / len(cases) if cases else 0.0
    print(f"\nScore: {passed_count}/{len(cases)} ({score:.0%})")
    if score >= (1.0 - 1e-9) and passed_count == len(cases):
        print("Evals passed.")
        return 0
    print("Evals failed (threshold: all must pass).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
