#!/usr/bin/env python3
"""PS6.6 — Bootstrap Kubernetes Secret for SpaceOps (dev/stage lab; never prints values)."""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# K8s Secret data key -> env var(s) to read (first non-empty wins).
SECRET_ENV_MAP: dict[str, tuple[str, ...]] = {
    "postgres-password": ("K8S_POSTGRES_PASSWORD", "POSTGRES_PASSWORD"),
    "OPENAI_API_KEY": ("OPENAI_API_KEY",),
    "APPROVAL_API_KEY": ("APPROVAL_API_KEY",),
    "GITHUB_TOKEN": ("GITHUB_TOKEN",),
    "NGC_API_KEY": ("NGC_API_KEY",),
    "CURSOR_SH_API_KEY": ("CURSOR_SH_API_KEY",),
    "GPU_LLM_API_KEY": ("GPU_LLM_API_KEY",),
}


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def require_tools(*tools: str) -> None:
    missing = [t for t in tools if not shutil.which(t)]
    if missing:
        raise SystemExit(f"Missing required tools: {', '.join(missing)}")


def resolve_env(key: str) -> str | None:
    for env_name in SECRET_ENV_MAP[key]:
        value = os.getenv(env_name, "").strip()
        if value:
            return value
    return None


def collect_secret_data(*, require_postgres: bool) -> dict[str, str]:
    data: dict[str, str] = {}
    for secret_key in SECRET_ENV_MAP:
        value = resolve_env(secret_key)
        if value:
            data[secret_key] = value
    if require_postgres and "postgres-password" not in data:
        raise SystemExit(
            "postgres-password required: set K8S_POSTGRES_PASSWORD or POSTGRES_PASSWORD"
        )
    if not data:
        raise SystemExit(
            "No secret values found in environment (see --help for env vars)"
        )
    return data


def apply_secret(
    namespace: str,
    secret_name: str,
    data: dict[str, str],
    *,
    dry_run: bool,
) -> None:
    encoded = {
        k: base64.b64encode(v.encode("utf-8")).decode("ascii") for k, v in data.items()
    }
    manifest = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": secret_name, "namespace": namespace},
        "type": "Opaque",
        "data": encoded,
    }
    payload = json.dumps(manifest)
    cmd = ["kubectl", "apply", "-f", "-"]
    if dry_run:
        cmd.insert(2, "--dry-run=client")
    proc = subprocess.run(cmd, input=payload, text=True, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(
            proc.stderr.strip() or proc.stdout.strip() or "kubectl apply failed"
        )
    action = "validated" if dry_run else "applied"
    keys = ", ".join(sorted(data))
    print(f"Secret {secret_name!r} in namespace {namespace!r} {action} (keys: {keys})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create or update SpaceOps Kubernetes Secret from environment variables."
    )
    parser.add_argument(
        "--namespace",
        default=os.getenv("K8S_NAMESPACE", "spaceops-dev"),
        help="Target namespace (default: K8S_NAMESPACE or spaceops-dev)",
    )
    parser.add_argument(
        "--secret-name",
        default=os.getenv("K8S_SECRET_NAME", "spaceops-dev-secrets"),
        help="Secret name (default: K8S_SECRET_NAME or spaceops-dev-secrets)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="kubectl apply --dry-run=client (no cluster change)",
    )
    parser.add_argument(
        "--create-namespace",
        action="store_true",
        help="kubectl create namespace if missing",
    )
    args = parser.parse_args()

    require_tools("kubectl")
    data = collect_secret_data(require_postgres=True)

    if args.create_namespace:
        proc = _run(
            ["kubectl", "create", "namespace", args.namespace],
            check=False,
        )
        if proc.returncode not in (0, 1) or (
            proc.returncode == 1 and "AlreadyExists" not in (proc.stderr or "")
        ):
            raise SystemExit(proc.stderr.strip() or "kubectl create namespace failed")

    apply_secret(args.namespace, args.secret_name, data, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
