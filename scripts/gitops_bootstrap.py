#!/usr/bin/env python3
"""PS6.7 — Install Argo CD and bootstrap SpaceOps GitOps Applications."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GITOPS_DIR = REPO_ROOT / "deploy" / "gitops" / "argocd"
ARGOCD_INSTALL_URL = os.getenv(
    "ARGOCD_INSTALL_URL",
    "https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml",
)
PLACEHOLDER_REPO = "__GITOPS_REPO_URL__"
PLACEHOLDER_REV = "__GITOPS_TARGET_REVISION__"


def _run(
    cmd: list[str], *, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=capture)


def require_tools(*tools: str) -> None:
    missing = [t for t in tools if not shutil.which(t)]
    if missing:
        raise SystemExit(f"Missing required tools: {', '.join(missing)}")


def git_remote_https_url() -> str | None:
    proc = _run(["git", "remote", "get-url", "origin"], check=False, capture=True)
    if proc.returncode != 0:
        return None
    raw = (proc.stdout or "").strip()
    if raw.startswith("git@"):
        # git@github.com:org/repo.git -> https://github.com/org/repo.git
        match = re.match(r"git@([^:]+):(.+?)(?:\.git)?$", raw)
        if match:
            return f"https://{match.group(1)}/{match.group(2)}.git"
    if raw.startswith("https://"):
        return raw if raw.endswith(".git") else f"{raw}.git"
    return raw


def resolve_repo_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    env = os.getenv("GITOPS_REPO_URL", "").strip()
    if env:
        return env
    remote = git_remote_https_url()
    if remote:
        return remote
    raise SystemExit(
        "Set GITOPS_REPO_URL or configure git remote origin (Argo CD needs HTTPS repo URL)."
    )


def resolve_target_revision(explicit: str | None) -> str:
    if explicit:
        return explicit
    return os.getenv("GITOPS_TARGET_REVISION", "main").strip() or "main"


def substitute_manifests(text: str, repo_url: str, revision: str) -> str:
    return text.replace(PLACEHOLDER_REPO, repo_url).replace(PLACEHOLDER_REV, revision)


def kubectl_apply_manifest(content: str) -> None:
    proc = subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=content,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise SystemExit(
            proc.stderr.strip() or proc.stdout.strip() or "kubectl apply failed"
        )


def install_argocd(*, dry_run: bool) -> None:
    require_tools("kubectl")
    if dry_run:
        print(f"Would apply Argo CD install from {ARGOCD_INSTALL_URL}")
        return
    _run(["kubectl", "create", "namespace", "argocd"], check=False)
    proc = subprocess.run(
        [
            "kubectl",
            "apply",
            "-n",
            "argocd",
            "--server-side",
            "--force-conflicts",
            "-f",
            ARGOCD_INSTALL_URL,
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or "Argo CD install failed")
    print("Argo CD install manifest applied (namespace argocd)")


def wait_argocd_server(timeout_seconds: int = 300) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        proc = _run(
            [
                "kubectl",
                "get",
                "deployment",
                "argocd-server",
                "-n",
                "argocd",
                "-o",
                "jsonpath={.status.availableReplicas}",
            ],
            check=False,
            capture=True,
        )
        if (proc.stdout or "").strip() == "1":
            print("argocd-server is available")
            return
        time.sleep(5)
    raise SystemExit("Timed out waiting for argocd-server")


def bootstrap_apps(
    repo_url: str,
    revision: str,
    *,
    include_dev: bool,
    dry_run: bool,
) -> None:
    require_tools("kubectl")
    files = [
        GITOPS_DIR / "namespace.yaml",
        GITOPS_DIR / "app-project.yaml",
        GITOPS_DIR / "root-application.yaml",
    ]
    if include_dev:
        files.append(GITOPS_DIR / "optional" / "spaceops-dev.yaml")
    for path in files:
        if not path.is_file():
            raise SystemExit(f"Missing manifest: {path}")
        text = substitute_manifests(
            path.read_text(encoding="utf-8"), repo_url, revision
        )
        if dry_run:
            print(f"Would apply {path.relative_to(REPO_ROOT)}")
            continue
        kubectl_apply_manifest(text)
        print(f"Applied {path.relative_to(REPO_ROOT)}")


def status() -> None:
    require_tools("kubectl")
    for kind, name in (
        ("appprojects.argoproj.io", "spaceops"),
        ("applications.argoproj.io", "spaceops-root"),
        ("applications.argoproj.io", "spaceops-stage"),
        ("applications.argoproj.io", "spaceops-prod"),
    ):
        proc = _run(
            ["kubectl", "get", kind, name, "-n", "argocd"],
            check=False,
            capture=True,
        )
        if proc.returncode == 0:
            print(proc.stdout.strip())
        else:
            print(f"{kind}/{name}: not found")


def main() -> None:
    parser = argparse.ArgumentParser(description="PS6.7 Argo CD GitOps bootstrap")
    sub = parser.add_subparsers(dest="command", required=True)

    p_install = sub.add_parser("install", help="Install Argo CD controller")
    p_install.add_argument("--dry-run", action="store_true")
    p_install.add_argument("--wait", action="store_true", help="Wait for argocd-server")

    p_boot = sub.add_parser("bootstrap", help="Apply AppProject + root Application")
    p_boot.add_argument("--repo-url", default=None)
    p_boot.add_argument("--revision", default=None)
    p_boot.add_argument("--include-dev", action="store_true")
    p_boot.add_argument("--dry-run", action="store_true")

    sub.add_parser("status", help="Show Argo CD Application status")

    args = parser.parse_args()

    if args.command == "install":
        install_argocd(dry_run=args.dry_run)
        if args.wait and not args.dry_run:
            wait_argocd_server()
        return

    if args.command == "bootstrap":
        repo = resolve_repo_url(args.repo_url)
        rev = resolve_target_revision(args.revision)
        print(f"GitOps repoURL={repo} targetRevision={rev}")
        bootstrap_apps(repo, rev, include_dev=args.include_dev, dry_run=args.dry_run)
        return

    if args.command == "status":
        status()
        return

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
