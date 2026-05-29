#!/usr/bin/env python3
"""PS5.7 host-side idle TTL check/stop for NIM container."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ACTIVITY_FILE = REPO_ROOT / "var" / "llm_last_gpu_call_at"
DEFAULT_COMPOSE_FILE = REPO_ROOT / "infra" / "docker-compose.yml"
DEFAULT_SERVICE = "nim-llm"


@dataclass
class IdleDecision:
    nim_running: bool
    last_activity: datetime | None
    idle_minutes: float | None
    ttl_minutes: int
    would_stop: bool
    reason: str


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stop NIM when idle past TTL.")
    p.add_argument(
        "--dry-run", action="store_true", help="Report decision without stopping."
    )
    p.add_argument(
        "--ttl-minutes",
        type=int,
        default=int(os.getenv("GPU_IDLE_TTL_MINUTES", "45") or 45),
        help="Idle TTL in minutes (default: env GPU_IDLE_TTL_MINUTES or 45).",
    )
    p.add_argument(
        "--activity-file",
        default=os.getenv("GPU_ACTIVITY_FILE") or str(DEFAULT_ACTIVITY_FILE),
        help=(
            "Host activity file path "
            "(default: env GPU_ACTIVITY_FILE or ./var/llm_last_gpu_call_at)."
        ),
    )
    p.add_argument(
        "--compose-file",
        default=str(DEFAULT_COMPOSE_FILE),
        help="docker-compose file path for stop action.",
    )
    p.add_argument(
        "--service",
        default=DEFAULT_SERVICE,
        help="Compose service name to stop (default nim-llm).",
    )
    p.add_argument(
        "--assume-nim-running",
        action="store_true",
        help="Testing/dev helper: bypass docker ps and assume NIM is running.",
    )
    p.add_argument(
        "--now-utc",
        default="",
        help="Testing helper: override current UTC time (ISO-8601).",
    )
    return p.parse_args()


def _parse_iso_utc(raw: str) -> datetime | None:
    val = (raw or "").strip()
    if not val:
        return None
    try:
        # Accept trailing Z and timezone-aware ISO string.
        val = val.replace("Z", "+00:00")
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        return None


def _nim_container_running(service: str) -> tuple[bool, str]:
    cmd = ["docker", "ps", "--filter", f"name={service}", "--format", "{{.Names}}"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return False, "docker_ps_failed"
    names = [n.strip() for n in (proc.stdout or "").splitlines() if n.strip()]
    return (len(names) > 0), ("running" if names else "not_running")


def evaluate_idle(
    *,
    ttl_minutes: int,
    activity_file: Path,
    service: str,
    now_utc: datetime | None = None,
    nim_running_override: bool | None = None,
) -> IdleDecision:
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    if nim_running_override is None:
        running, state_reason = _nim_container_running(service)
    else:
        running, state_reason = nim_running_override, "assumed_running"
    if not running:
        return IdleDecision(
            nim_running=False,
            last_activity=None,
            idle_minutes=None,
            ttl_minutes=ttl_minutes,
            would_stop=False,
            reason=state_reason,
        )

    raw = ""
    if activity_file.exists():
        raw = activity_file.read_text(encoding="utf-8").strip()
    last = _parse_iso_utc(raw)
    if last is None:
        # Required behavior in PS5.7: missing file while NIM is up means treat as idle.
        return IdleDecision(
            nim_running=True,
            last_activity=None,
            idle_minutes=float(ttl_minutes + 1),
            ttl_minutes=ttl_minutes,
            would_stop=True,
            reason="missing_or_invalid_activity_file",
        )

    idle = max(0.0, (now - last).total_seconds() / 60.0)
    return IdleDecision(
        nim_running=True,
        last_activity=last,
        idle_minutes=idle,
        ttl_minutes=ttl_minutes,
        would_stop=idle >= ttl_minutes,
        reason="idle_ttl_exceeded" if idle >= ttl_minutes else "recent_activity",
    )


def _stop_nim(*, compose_file: str, service: str) -> int:
    cmd = [
        "docker",
        "compose",
        "-f",
        compose_file,
        "--project-directory",
        str(REPO_ROOT),
        "--profile",
        "gpu",
        "stop",
        service,
    ]
    return subprocess.call(cmd)


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "n/a"
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    args = _parse_args()
    ttl = max(1, int(args.ttl_minutes))
    activity = Path(args.activity_file)
    now_override = _parse_iso_utc(args.now_utc) if args.now_utc else None
    if args.assume_nim_running:
        decision = evaluate_idle(
            ttl_minutes=ttl,
            activity_file=activity,
            service=args.service,
            now_utc=now_override,
            nim_running_override=True,
        )
    else:
        decision = evaluate_idle(
            ttl_minutes=ttl,
            activity_file=activity,
            service=args.service,
            now_utc=now_override,
        )
    idle_str = (
        "n/a" if decision.idle_minutes is None else f"{decision.idle_minutes:.2f}"
    )

    print(f"nim_running={str(decision.nim_running).lower()}")
    print(f"activity_file={activity}")
    print(f"last_activity_utc={_fmt_dt(decision.last_activity)}")
    print(f"idle_minutes={idle_str}")
    print(f"ttl_minutes={decision.ttl_minutes}")
    print(f"would_stop={str(decision.would_stop).lower()}")
    print(f"reason={decision.reason}")

    if args.dry_run:
        return 0

    if not decision.would_stop:
        return 0
    rc = _stop_nim(compose_file=args.compose_file, service=args.service)
    return int(rc)


if __name__ == "__main__":
    sys.exit(main())
