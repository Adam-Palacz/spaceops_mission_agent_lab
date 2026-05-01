from __future__ import annotations

import sys

from scripts import replay_run


def test_replay_cli_exit_code_0(monkeypatch, capsys):
    monkeypatch.setattr(
        replay_run,
        "replay_by_run_id",
        lambda _run_id: {"comparison": {"has_diff": False}},
    )
    monkeypatch.setattr(sys, "argv", ["replay_run.py", "--run-id", "r-1"])
    code = replay_run.main()
    captured = capsys.readouterr()
    assert code == 0
    assert "no core behavior differences" in captured.out


def test_replay_cli_exit_code_2_when_diff(monkeypatch, capsys):
    monkeypatch.setattr(
        replay_run,
        "replay_by_run_id",
        lambda _run_id: {"comparison": {"has_diff": True}},
    )
    monkeypatch.setattr(sys, "argv", ["replay_run.py", "--run-id", "r-2"])
    code = replay_run.main()
    captured = capsys.readouterr()
    assert code == 2
    assert "behavior differences" in captured.out


def test_replay_cli_exit_code_1_on_missing(monkeypatch, capsys):
    def _missing(_run_id: str):
        raise FileNotFoundError("not found")

    monkeypatch.setattr(replay_run, "replay_by_run_id", _missing)
    monkeypatch.setattr(sys, "argv", ["replay_run.py", "--run-id", "r-3"])
    code = replay_run.main()
    captured = capsys.readouterr()
    assert code == 1
    assert "Replay failed" in captured.out
