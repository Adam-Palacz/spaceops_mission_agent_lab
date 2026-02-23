"""
S1.11: Evals — case format, scoring logic, must-escalate.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Add repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_cases() -> list[dict]:
    from evals.scoring import load_cases as _load
    return _load()


def test_cases_yaml_has_required_count():
    """S1.11: At least 5 cases, at least one must-escalate."""
    cases = load_cases()
    assert len(cases) >= 5, "evals/cases.yaml must have at least 5 cases"
    must_escalate = [c for c in cases if c.get("must_escalate") is True]
    assert len(must_escalate) >= 1, "At least one case must have must_escalate: true"


def test_case_format_has_payload_and_expectations():
    """Each case has payload and expected_subsystem or must_escalate."""
    cases = load_cases()
    for case in cases:
        assert "id" in case
        assert "payload" in case
        assert case.get("must_escalate") is True or case.get("expected_subsystem"), (
            f"Case {case.get('id')}: need expected_subsystem or must_escalate"
        )


def test_scoring_module_runs_and_outputs_score():
    """S1.11: python -m evals.scoring runs and outputs score/pass per case."""
    result = subprocess.run(
        [sys.executable, "-m", "evals.scoring"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        env={**__import__("os").environ},
    )
    out = result.stdout + result.stderr
    assert "Score:" in out or "PASS" in out or "FAIL" in out, "Output must show score or pass/fail per case"
    # If API key missing, may exit 1; we only require the script runs and produces expected output
    assert "evals" in out.lower() or "PASS" in out or "FAIL" in out or "OPENAI" in out or "Error" in out


# --- S1.15 evals hardening: top_k and require_citations vs escalation ---


def test_score_case_triage_respects_top_k():
    """S1.15: triage pass only when actual is in expected_subsystem[:top_k]."""
    from evals.scoring import score_case

    # top_k=1: only first subsystem allowed
    case_top1 = {"expected_subsystem_top_k": 1, "expected_subsystem": ["Power", "Thermal"], "must_escalate": False}
    passed, failures = score_case(case_top1, {"subsystem": "Power", "escalated": False})
    assert passed, failures
    passed, failures = score_case(case_top1, {"subsystem": "Thermal", "escalated": False})
    assert not passed and any("triage" in f for f in failures)

    # top_k=2: first two allowed
    case_top2 = {"expected_subsystem_top_k": 2, "expected_subsystem": ["ADCS", "Payload"], "must_escalate": False}
    for sub in ("ADCS", "Payload"):
        passed, _ = score_case(case_top2, {"subsystem": sub, "escalated": False})
        assert passed, f"top_2 should allow {sub}"
    passed, failures = score_case(case_top2, {"subsystem": "Power", "escalated": False})
    assert not passed and any("triage" in f for f in failures)

    # default top_k=1 when missing
    case_no_top_k = {"expected_subsystem": ["A", "B"], "must_escalate": False}
    passed, _ = score_case(case_no_top_k, {"subsystem": "A", "escalated": False})
    assert passed
    passed, failures = score_case(case_no_top_k, {"subsystem": "B", "escalated": False})
    assert not passed and any("triage" in f for f in failures)


def test_score_case_require_citations_fails_when_escalated():
    """S1.15: case with require_citations and not must_escalate fails when run escalated."""
    from evals.scoring import score_case

    case = {"require_citations": True, "must_escalate": False, "expected_subsystem": ["Power"], "expected_subsystem_top_k": 1}
    result_escalated = {"subsystem": "Power", "escalated": True, "escalation_packet": {"reason": "no_evidence"}}
    passed, failures = score_case(case, result_escalated)
    assert not passed, "require_citations + escalated must fail"
    assert any("require_citations" in f and "escalated" in f for f in failures)

    result_not_escalated_no_citations = {"subsystem": "Power", "escalated": False, "citations": [], "report": {}}
    passed, failures = score_case(case, result_not_escalated_no_citations)
    assert not passed
    assert any("citation" in f.lower() for f in failures)

    result_not_escalated_with_citations = {"subsystem": "Power", "escalated": False, "citations": [{"doc_id": "x"}], "report": {"citation_refs": ["x"]}}
    passed, failures = score_case(case, result_not_escalated_with_citations)
    assert passed, failures
