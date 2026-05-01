from __future__ import annotations

from evals.scoring import run_selected_standard_cases


def test_run_selected_standard_cases_reports_missing_case():
    code = run_selected_standard_cases(["__missing_case__"])
    assert code == 1


def test_run_selected_standard_cases_pass(monkeypatch):
    monkeypatch.setattr(
        "evals.scoring.load_cases",
        lambda: [
            {
                "id": "gate-pass",
                "payload": {"message": "x"},
                "expected_subsystem": ["Power"],
                "expected_subsystem_top_k": 1,
                "must_escalate": False,
            }
        ],
    )
    monkeypatch.setattr(
        "evals.scoring.run_case",
        lambda case: {"subsystem": "Power", "escalated": False},
    )
    code = run_selected_standard_cases(["gate-pass"])
    assert code == 0


def test_run_selected_standard_cases_fail_with_reason(monkeypatch):
    monkeypatch.setattr(
        "evals.scoring.load_cases",
        lambda: [
            {
                "id": "gate-fail",
                "payload": {"message": "x"},
                "expected_subsystem": ["Power"],
                "expected_subsystem_top_k": 1,
                "must_escalate": False,
            }
        ],
    )
    monkeypatch.setattr(
        "evals.scoring.run_case",
        lambda case: {"subsystem": "Thermal", "escalated": False},
    )
    code = run_selected_standard_cases(["gate-fail"])
    assert code == 1
