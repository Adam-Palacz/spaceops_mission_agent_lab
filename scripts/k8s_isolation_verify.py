#!/usr/bin/env python3
"""PS6.5 verify namespace isolation controls on a live cluster."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from k8s_cluster_cni import require_network_policy_cni_or_exit  # noqa: E402

NAMESPACE = os.getenv("K8S_NAMESPACE", "spaceops-dev")
HELM_RELEASE = os.getenv("K8S_HELM_RELEASE", "spaceops")
PROBE_NAMESPACE = os.getenv("K8S_ISOLATION_PROBE_NS", "spaceops-prod-isolation-probe")
API_DEPLOYMENT = f"{HELM_RELEASE}-api"
API_SA = f"{HELM_RELEASE}-api"


def _run(
    cmd: list[str], *, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=capture)


def require_tools(*tools: str) -> None:
    missing = [t for t in tools if not shutil.which(t)]
    if missing:
        raise SystemExit(f"Missing required tools: {', '.join(missing)}")


def check_isolation_resources() -> None:
    for kind in ("networkpolicy", "resourcequota", "limitrange", "role"):
        proc = _run(
            ["kubectl", "get", kind, "-n", NAMESPACE],
            check=False,
            capture=True,
        )
        if proc.returncode != 0 or not (proc.stdout or "").strip():
            raise SystemExit(f"Expected {kind} resources in {NAMESPACE!r}")
        print(f"[ok] {kind} present in {NAMESPACE}")


def check_network_policy_cni_present() -> None:
    require_network_policy_cni_or_exit()


def check_app_sa_no_cluster_admin() -> None:
    proc = _run(
        [
            "kubectl",
            "auth",
            "can-i",
            "patch",
            "nodes",
            f"--as=system:serviceaccount:{NAMESPACE}:{API_SA}",
            "-n",
            NAMESPACE,
        ],
        check=False,
        capture=True,
    )
    answer = (proc.stdout or "").strip().lower()
    if answer == "yes":
        raise SystemExit(f"ServiceAccount {API_SA} must not patch nodes")
    print(f"[ok] {API_SA} cannot patch nodes (auth can-i: {answer or 'no'})")


def check_cross_namespace_blocked() -> None:
    """Create probe Service in another namespace; curl from API pod should fail."""
    _run(
        ["kubectl", "delete", "namespace", PROBE_NAMESPACE, "--ignore-not-found"],
        check=False,
    )
    _run(["kubectl", "create", "namespace", PROBE_NAMESPACE])
    try:
        _run(
            [
                "kubectl",
                "create",
                "deployment",
                "probe-nginx",
                "-n",
                PROBE_NAMESPACE,
                "--image=nginx:1.27-alpine",
                "--port=80",
            ]
        )
        _run(
            [
                "kubectl",
                "wait",
                "-n",
                PROBE_NAMESPACE,
                "--for=condition=available",
                "deployment/probe-nginx",
                "--timeout=120s",
            ]
        )
        target = f"probe-nginx.{PROBE_NAMESPACE}.svc.cluster.local"
        proc = _run(
            [
                "kubectl",
                "exec",
                "-n",
                NAMESPACE,
                f"deployment/{API_DEPLOYMENT}",
                "--",
                "python",
                "-c",
                (
                    "import socket,sys; "
                    f"s=socket.create_connection(('{target}',80),2); "
                    "s.close()"
                ),
            ],
            check=False,
            capture=True,
        )
        if proc.returncode == 0:
            raise SystemExit(
                f"Cross-namespace reachability to {target} should be blocked by NetworkPolicy"
            )
        print(f"[ok] API pod cannot reach {target} (expected failure)")
    finally:
        _run(
            ["kubectl", "delete", "namespace", PROBE_NAMESPACE, "--wait=false"],
            check=False,
        )
        time.sleep(2)


def run_verify(*, skip_cross_ns: bool) -> None:
    require_tools("kubectl")
    ctx = _run(["kubectl", "config", "current-context"], capture=True)
    print(f"kubectl context: {(ctx.stdout or '').strip()}")
    check_isolation_resources()
    check_app_sa_no_cluster_admin()
    if not skip_cross_ns:
        check_network_policy_cni_present()
        check_cross_namespace_blocked()
    print("\nPS6.5 isolation verification passed.")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PS6.5 K8s environment isolation checks")
    p.add_argument(
        "--skip-cross-ns",
        action="store_true",
        help="Skip cross-namespace probe (creates/deletes temporary namespace)",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        run_verify(skip_cross_ns=args.skip_cross_ns)
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc.stdout or str(exc), file=sys.stderr)
        raise SystemExit(exc.returncode) from exc


if __name__ == "__main__":
    main()
