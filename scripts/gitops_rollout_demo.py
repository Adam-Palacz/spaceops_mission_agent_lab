#!/usr/bin/env python3
"""PS6.7 GitOps rollout demo — sync after Git tag change + rollback via revert (requires Argo CD)."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GITOPS_VALUES = REPO_ROOT / "deploy" / "helm" / "spaceops" / "values-gitops-stage.yaml"
APP_NAME = os.getenv("GITOPS_APP_NAME", "spaceops-stage")
NAMESPACE = os.getenv("GITOPS_APP_NAMESPACE", "spaceops-stage")
ARGO_NAMESPACE = os.getenv("ARGOCD_NAMESPACE", "argocd")
API_DEPLOYMENT = os.getenv("K8S_HELM_RELEASE", "spaceops") + "-api"


def _run(
    cmd: list[str], *, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=capture)


def require_tools(*tools: str) -> None:
    missing = [t for t in tools if not shutil.which(t)]
    if missing:
        raise SystemExit(f"Missing required tools: {', '.join(missing)}")


def pre_checks() -> None:
    require_tools("kubectl")
    proc = _run(
        ["kubectl", "get", "application", APP_NAME, "-n", ARGO_NAMESPACE],
        check=False,
        capture=True,
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"Argo CD Application {APP_NAME!r} not found — run `make gitops-install && make gitops-bootstrap` "
            f"and push deploy/gitops/ to Git remote first."
        )
    print(f"Application {APP_NAME} present in {ARGO_NAMESPACE}")


def api_image_tag() -> str:
    proc = _run(
        [
            "kubectl",
            "get",
            "deployment",
            API_DEPLOYMENT,
            "-n",
            NAMESPACE,
            "-o",
            "jsonpath={.spec.template.spec.containers[0].image}",
        ],
        check=False,
        capture=True,
    )
    image = (proc.stdout or "").strip()
    if not image or proc.returncode != 0:
        return "(deployment not ready)"
    return image.split(":")[-1] if ":" in image else image


def sync_application() -> None:
    if shutil.which("argocd"):
        print(f"Syncing {APP_NAME} via argocd CLI...")
        _run(["argocd", "app", "sync", APP_NAME, "--grpc-web"])
        _run(["argocd", "app", "wait", APP_NAME, "--health", "--timeout", "600"])
        return
    print(
        "argocd CLI not on PATH — trigger sync via UI or install argocd. "
        "Falling back to kubectl refresh annotation..."
    )
    _run(
        [
            "kubectl",
            "patch",
            "application",
            APP_NAME,
            "-n",
            ARGO_NAMESPACE,
            "--type",
            "merge",
            "-p",
            '{"metadata":{"annotations":{"spaceops.io/refresh":"'
            + str(int(time.time()))
            + '"}}}',
        ]
    )
    print("Annotated Application — wait for Argo CD controller to reconcile.")


def wait_rollout() -> None:
    proc = _run(
        [
            "kubectl",
            "rollout",
            "status",
            f"deployment/{API_DEPLOYMENT}",
            "-n",
            NAMESPACE,
            "--timeout=300s",
        ],
        check=False,
        capture=True,
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        raise SystemExit(f"Rollout did not complete for {API_DEPLOYMENT}")
    print(f"Rollout complete; image tag: {api_image_tag()}")


def print_gitops_flow() -> None:
    print(
        """
GitOps promotion flow (stage):
  1. Edit deploy/helm/spaceops/values-gitops-stage.yaml (images.api.tag / images.mcp.tag)
  2. git commit && git push
  3. make gitops-rollout-demo   # or: argocd app sync spaceops-stage

Rollback (same as PS6.4 Fallback A):
  1. git revert <commit>
  2. git push
  3. argocd app sync spaceops-stage   # prod: manual sync after approver

Drift: stage has selfHeal — kubectl edit is reverted on sync. Fix Git, then sync.
See docs/runbooks/gitops_bootstrap.md and docs/runbooks/k8s_rollout_rollback.md#rollback-flow
"""
    )


def run_demo(*, sync_only: bool) -> None:
    pre_checks()
    print(f"Current API image tag: {api_image_tag()}")
    print(f"GitOps values file: {GITOPS_VALUES.relative_to(REPO_ROOT)}")
    if not sync_only:
        print_gitops_flow()
        print("After you push a tag change to Git, re-run with --sync-only")
        return
    sync_application()
    wait_rollout()
    print("\nPS6.7 GitOps sync demo complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="PS6.7 GitOps rollout / rollback demo")
    parser.add_argument(
        "--sync-only",
        action="store_true",
        help="Sync Application and wait for rollout (run after git push)",
    )
    args = parser.parse_args()
    try:
        run_demo(sync_only=args.sync_only)
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc.stdout or str(exc), file=sys.stderr)
        raise SystemExit(exc.returncode) from exc


if __name__ == "__main__":
    main()
