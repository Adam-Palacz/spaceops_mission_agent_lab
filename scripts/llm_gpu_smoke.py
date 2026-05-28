#!/usr/bin/env python3
"""
PS5.3 — NIM health check and one gateway completion (operator smoke).

Examples:
  python scripts/llm_gpu_smoke.py --wait-health --timeout 300
  LLM_BACKEND=gpu python scripts/llm_gpu_smoke.py --generate
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.llm_backends.nim_client import (  # noqa: E402
    check_nim_health,
    gpu_activity_path,
    nim_health_url,
)
from apps.llm_backends.registry import resolve_llm_backend  # noqa: E402
from apps.llm_gateway import generate  # noqa: E402
from config import settings  # noqa: E402


def _wait_health(timeout_s: int) -> int:
    url = nim_health_url()
    if not url:
        print("GPU_LLM_BASE_URL is not set", file=sys.stderr)
        return 1
    print(f"Waiting for NIM health at {url} (timeout={timeout_s}s)...")
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if check_nim_health():
            print("NIM health: OK")
            return 0
        time.sleep(5)
    print("NIM health: TIMEOUT", file=sys.stderr)
    return 1


def _generate_smoke() -> int:
    backend = resolve_llm_backend()
    if backend != "gpu":
        print(
            f"LLM_BACKEND must be 'gpu' for smoke generate (got {backend!r})",
            file=sys.stderr,
        )
        return 1
    model = (getattr(settings, "gpu_llm_model_id", "") or "").strip()
    if not model:
        print("Set GPU_LLM_MODEL_ID for NIM model name", file=sys.stderr)
        return 1
    try:
        out = generate(
            prompt="Reply with exactly: nim-smoke-ok",
            node="llm_gpu_smoke",
            model_id=model,
            temperature=0,
        )
    except Exception as exc:
        print(f"generate() failed: {exc}", file=sys.stderr)
        return 1
    content = (out.get("content") or "").strip()
    if not content:
        print("generate() returned empty content", file=sys.stderr)
        return 1
    if out.get("backend_actual") != "gpu":
        print(
            f"backend_actual={out.get('backend_actual')!r} (expected 'gpu')",
            file=sys.stderr,
        )
        return 1
    activity = gpu_activity_path()
    if activity.is_file():
        print(
            f"activity file: {activity} -> {activity.read_text(encoding='utf-8').strip()}"
        )
    print(
        f"generate OK backend_actual=gpu model_id={out.get('model_id')} "
        f"content_len={len(content)}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="NIM GPU backend smoke (PS5.3)")
    parser.add_argument(
        "--wait-health",
        action="store_true",
        help="Poll GET /v1/health/ready until success or timeout",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Run one generate() via gateway (requires LLM_BACKEND=gpu)",
    )
    parser.add_argument(
        "--health-only",
        action="store_true",
        help="Single health check (exit 0 if ready)",
    )
    parser.add_argument(
        "--timeout", type=int, default=300, help="Health wait timeout seconds"
    )
    args = parser.parse_args()

    if not any((args.wait_health, args.generate, args.health_only)):
        parser.error("Specify --wait-health, --health-only, and/or --generate")

    rc = 0
    if args.health_only:
        ok = check_nim_health()
        print(f"NIM health: {'OK' if ok else 'FAIL'} ({nim_health_url()})")
        rc = 0 if ok else 1
    if args.wait_health and rc == 0:
        rc = _wait_health(args.timeout)
    if args.generate and rc == 0:
        rc = _generate_smoke()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
