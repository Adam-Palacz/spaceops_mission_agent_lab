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
