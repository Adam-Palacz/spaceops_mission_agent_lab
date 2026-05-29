#!/usr/bin/env python3
"""PS5.7 operator acceptance: containerized API writes host-visible GPU activity."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ACTIVITY_FILE = REPO_ROOT / "var" / "llm_last_gpu_call_at"
IDLE_SCRIPT = REPO_ROOT / "scripts" / "gpu_idle_shutdown.py"


def _parse_iso_utc(raw: str) -> datetime:
    value = raw.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _wait_api(api_base_url: str, timeout_s: int) -> None:
    deadline = time.monotonic() + timeout_s
    url = f"{api_base_url.rstrip('/')}/health"
    last_error = ""
    with httpx.Client(timeout=10.0, trust_env=False) as client:
        while time.monotonic() < deadline:
            try:
                resp = client.get(url)
                if resp.status_code == 200:
                    print(f"API health: OK ({url})")
                    return
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            except Exception as exc:
                last_error = str(exc)
            time.sleep(5)
    raise RuntimeError(f"API health did not become ready at {url}: {last_error}")


def _post_run(api_base_url: str, timeout_s: int) -> dict:
    url = f"{api_base_url.rstrip('/')}/runs"
    incident_id = f"ps57-gpu-activity-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    payload = {
        "incident_id": incident_id,
        "payload": {
            "subsystem": "Power",
            "risk": "low",
            "message": "PS5.7 GPU activity integration check",
            "time_range_start": "2026-05-28T10:00:00Z",
            "time_range_end": "2026-05-28T10:30:00Z",
        },
    }
    print(f"POST {url} incident_id={incident_id}")
    with httpx.Client(timeout=timeout_s, trust_env=False) as client:
        resp = client.post(url, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(
            f"POST /runs failed HTTP {resp.status_code}: {resp.text[:1000]}"
        )
    body = resp.json()
    if body.get("status") != "completed":
        raise RuntimeError(
            f"POST /runs returned unexpected body: {json.dumps(body)[:1000]}"
        )
    return body


def _read_fresh_activity(activity_file: Path, started_at: datetime) -> datetime:
    if not activity_file.is_file():
        raise RuntimeError(f"Activity file was not written: {activity_file}")
    raw = activity_file.read_text(encoding="utf-8").strip()
    if not raw:
        raise RuntimeError(f"Activity file is empty: {activity_file}")
    activity_at = _parse_iso_utc(raw)
    if activity_at < started_at:
        raise RuntimeError(
            f"Activity timestamp is stale: {activity_at.isoformat()} < "
            f"{started_at.isoformat()}"
        )
    print(f"activity file: {activity_file} -> {raw}")
    return activity_at


def _prepare_activity_file(activity_file: Path) -> None:
    activity_file.parent.mkdir(parents=True, exist_ok=True)
    if activity_file.exists():
        activity_file.unlink()


def _idle_dry_run(activity_file: Path, ttl_minutes: int) -> None:
    cmd = [
        sys.executable,
        str(IDLE_SCRIPT),
        "--dry-run",
        "--activity-file",
        str(activity_file),
        "--ttl-minutes",
        str(ttl_minutes),
    ]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    print(proc.stdout, end="")
    if proc.returncode != 0:
        raise RuntimeError(f"gpu_idle_shutdown.py failed: {proc.stderr.strip()}")
    if "would_stop=false" not in proc.stdout:
        raise RuntimeError(
            "Idle dry-run did not report would_stop=false after fresh activity."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify PS5.7 end-to-end: API in Compose writes ./var/llm_last_gpu_call_at "
            "and host idle dry-run sees recent activity."
        )
    )
    parser.add_argument("--api-base-url", default="http://localhost:8000")
    parser.add_argument("--activity-file", type=Path, default=DEFAULT_ACTIVITY_FILE)
    parser.add_argument("--wait-api-timeout", type=int, default=180)
    parser.add_argument("--run-timeout", type=int, default=600)
    parser.add_argument("--ttl-minutes", type=int, default=45)
    args = parser.parse_args()

    try:
        _prepare_activity_file(args.activity_file)
        started_at = datetime.now(UTC).replace(microsecond=0)
        _wait_api(args.api_base_url, args.wait_api_timeout)
        body = _post_run(args.api_base_url, args.run_timeout)
        print(f"run completed: run_id={body.get('run_id')}")
        _read_fresh_activity(args.activity_file, started_at)
        _idle_dry_run(args.activity_file, args.ttl_minutes)
    except Exception as exc:
        print(f"PS5.7 GPU activity integration failed: {exc}", file=sys.stderr)
        return 1
    print("PS5.7 GPU activity integration: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
