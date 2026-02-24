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
    S1.15: uses expected_subsystem_top_k; require_citations fails when run escalated.
    """
    failures: list[str] = []
    must_escalate = case.get("must_escalate") is True

    # Triage: subsystem must be in first top_k of expected_subsystem (S1.15). Skip for must_escalate cases (we only assert escalation).
    expected_subsystem: list[str] = case.get("expected_subsystem") or []
    top_k = case.get("expected_subsystem_top_k")
    if top_k is None or not isinstance(top_k, int):
        top_k = 1
    if expected_subsystem and not must_escalate:
        actual = (result.get("subsystem") or "").strip()
        allowed = expected_subsystem[:top_k]
        if actual not in allowed:
            failures.append(f"triage: expected one of {allowed} (top_{top_k}), got '{actual}'")

    # Must escalate
    escalated = result.get("escalated") is True
    escalation_packet = result.get("escalation_packet") or {}
    if must_escalate:
        if not escalated:
            failures.append("must_escalate: expected escalation, agent did not escalate")
        elif not escalation_packet.get("reason"):
            failures.append("must_escalate: expected escalation_packet with reason")
    else:
        # S1.15: require_citations + escalation => fail (do not allow escalation to "rescue" citation case)
        if case.get("require_citations") and escalated:
            failures.append("require_citations: expected citations but run escalated")

    # Citation presence (when not must_escalate and require_citations, and did not escalate)
    if case.get("require_citations") and not must_escalate and not escalated:
        citations = result.get("citations") or []
        report = result.get("report") or {}
        refs = report.get("citation_refs") or []
        if len(citations) == 0 and len(refs) == 0:
            failures.append("require_citations: expected at least one citation or citation_ref")

    passed = len(failures) == 0
    return passed, failures


def main() -> int:
    cases = load_cases()
    if not cases:
        print("No cases in evals/cases.yaml")
        return 1

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
