from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PY = REPO_ROOT / "scripts" / "gpu_idle_shutdown.py"
SCRIPT_SH = REPO_ROOT / "scripts" / "gpu_idle_shutdown.sh"
SCRIPT_PS1 = REPO_ROOT / "scripts" / "gpu_idle_shutdown.ps1"


def _run(
    args: list[str], env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        env=env,
    )


def _bash_path(path: Path) -> str:
    if os.name != "nt":
        return str(path)
    drive = path.drive.rstrip(":").lower()
    rest = path.as_posix().split(":", 1)[-1].lstrip("/")
    if not drive or not rest:
        pytest.skip(f"Cannot convert Windows path for bash: {path}")
    converters = (
        ("wslpath", f"/mnt/{drive}/{rest}"),
        ("cygpath", f"/{drive}/{rest}"),
    )
    for converter, converted in converters:
        try:
            proc = subprocess.run(
                ["bash", "-lc", f"command -v {converter} >/dev/null"],
                text=True,
                capture_output=True,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            continue
        if proc.returncode == 0:
            return converted
    pytest.skip("No bash path converter (wslpath/cygpath) available on Windows.")


def test_ps57_dry_run_python_with_recent_timestamp(tmp_path: Path):
    activity = tmp_path / "llm_last_gpu_call_at"
    activity.write_text("2026-05-28T10:10:00Z\n", encoding="utf-8")
    proc = _run(
        [
            sys.executable,
            str(SCRIPT_PY),
            "--dry-run",
            "--assume-nim-running",
            "--activity-file",
            str(activity),
            "--ttl-minutes",
            "45",
            "--now-utc",
            "2026-05-28T10:20:00Z",
        ]
    )
    assert proc.returncode == 0, proc.stderr
    assert "would_stop=false" in proc.stdout
    assert "ttl_minutes=45" in proc.stdout
    assert "last_activity_utc=2026-05-28T10:10:00Z" in proc.stdout


def test_ps57_dry_run_python_missing_activity_would_stop(tmp_path: Path):
    activity = tmp_path / "missing_activity"
    proc = _run(
        [
            sys.executable,
            str(SCRIPT_PY),
            "--dry-run",
            "--assume-nim-running",
            "--activity-file",
            str(activity),
            "--ttl-minutes",
            "45",
            "--now-utc",
            "2026-05-28T10:20:00Z",
        ]
    )
    assert proc.returncode == 0, proc.stderr
    assert "would_stop=true" in proc.stdout
    assert "reason=missing_or_invalid_activity_file" in proc.stdout


def test_ps57_python_uses_gpu_activity_file_env_by_default(tmp_path: Path):
    activity = tmp_path / "env_activity"
    activity.write_text("2026-05-28T10:10:00Z\n", encoding="utf-8")
    env = {**os.environ, "GPU_ACTIVITY_FILE": str(activity)}
    proc = _run(
        [
            sys.executable,
            str(SCRIPT_PY),
            "--dry-run",
            "--assume-nim-running",
            "--ttl-minutes",
            "45",
            "--now-utc",
            "2026-05-28T10:20:00Z",
        ],
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert f"activity_file={activity}" in proc.stdout
    assert "would_stop=false" in proc.stdout


def test_ps57_dry_run_bash_wrapper(tmp_path: Path):
    if shutil.which("bash") is None:
        pytest.skip("bash not found")
    activity = tmp_path / "llm_last_gpu_call_at"
    activity.write_text("2026-05-28T10:10:00Z\n", encoding="utf-8")
    script = _bash_path(SCRIPT_SH)
    activity_arg = _bash_path(activity)
    proc = _run(
        [
            "bash",
            script,
            "--dry-run",
            "--assume-nim-running",
            "--activity-file",
            activity_arg,
            "--ttl-minutes",
            "45",
            "--now-utc",
            "2026-05-28T10:20:00Z",
        ]
    )
    assert proc.returncode == 0, proc.stderr
    assert "would_stop=false" in proc.stdout


def test_ps57_dry_run_powershell_wrapper(tmp_path: Path):
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if pwsh is None:
        pytest.skip("PowerShell not found")
    activity = tmp_path / "llm_last_gpu_call_at"
    activity.write_text("2026-05-28T10:10:00Z\n", encoding="utf-8")
    proc = _run(
        [
            pwsh,
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT_PS1),
            "-DryRun",
            "-ActivityFile",
            str(activity),
            "-TtlMinutes",
            "45",
            "--assume-nim-running",
            "--now-utc",
            "2026-05-28T10:20:00Z",
        ]
    )
    # Forwarded args after -File are passed to Python wrapper.
    assert proc.returncode == 0, proc.stderr
    assert "would_stop=false" in proc.stdout
