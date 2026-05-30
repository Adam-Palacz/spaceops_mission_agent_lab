#!/usr/bin/env python3
"""PS6.3 local Kubernetes bootstrap (kind + Helm minimal dev profile)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPO_ROOT / "infra" / "docker-compose.yml"
KIND_CONFIG = REPO_ROOT / "infra" / "k8s" / "local" / "kind-config.yaml"
HELM_CHART = REPO_ROOT / "deploy" / "helm" / "spaceops"
CLUSTER_NAME = os.getenv("K8S_CLUSTER_NAME", "spaceops-dev")
HELM_RELEASE = os.getenv("K8S_HELM_RELEASE", "spaceops")
NAMESPACE = os.getenv("K8S_NAMESPACE", "spaceops-dev")
API_LOCAL_PORT = int(os.getenv("K8S_API_LOCAL_PORT", "18000"))
POSTGRES_PASSWORD = os.getenv("K8S_POSTGRES_PASSWORD", "spaceops")
MINIMAL_SERVICES = ("api", "telemetry-mcp")
IMAGE_API = os.getenv("K8S_IMAGE_API", "spaceops-api:local")
IMAGE_MCP = os.getenv("K8S_IMAGE_MCP", "spaceops-mcp:local")


def _run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = False,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture,
        cwd=str(cwd or REPO_ROOT),
    )


def _which(name: str) -> str | None:
    return shutil.which(name)


def require_tools(*tools: str) -> None:
    missing = [t for t in tools if not _which(t)]
    if missing:
        raise SystemExit(f"Missing required tools on PATH: {', '.join(missing)}")


def kind_cluster_exists() -> bool:
    proc = _run(["kind", "get", "clusters"], capture=True)
    return CLUSTER_NAME in (proc.stdout or "").split()


def compose_cmd(*args: str) -> list[str]:
    return [
        "docker",
        "compose",
        "-f",
        str(COMPOSE_FILE),
        "--project-directory",
        str(REPO_ROOT),
        *args,
    ]


def compose_project_name() -> str:
    proc = _run(compose_cmd("config", "--format", "json"), capture=True)
    return json.loads(proc.stdout or "{}").get("name") or REPO_ROOT.name


def compose_built_image_ref(service: str) -> str:
    """Local tag Compose assigns after `docker compose build` (project-service:latest)."""
    return f"{compose_project_name()}-{service}:latest"


def build_and_tag_images(*, skip_build: bool = False) -> None:
    if not skip_build:
        print(f"Building compose images: {', '.join(MINIMAL_SERVICES)}")
        _run(compose_cmd("build", *MINIMAL_SERVICES))
    for service, tag in (("api", IMAGE_API), ("telemetry-mcp", IMAGE_MCP)):
        source = compose_built_image_ref(service)
        proc = _run(
            ["docker", "image", "inspect", "-f", "{{.Id}}", source],
            capture=True,
            check=False,
        )
        if proc.returncode != 0:
            raise SystemExit(
                f"Missing built image {source!r}; compose build may have failed for {service!r}"
            )
        _run(["docker", "tag", source, tag])
        print(f"Tagged {source} -> {tag}")


def ensure_kind_cluster(*, skip_calico: bool = False) -> None:
    created = False
    if kind_cluster_exists():
        print(f"kind cluster {CLUSTER_NAME!r} already exists")
    else:
        print(f"Creating kind cluster {CLUSTER_NAME!r}")
        _run(
            [
                "kind",
                "create",
                "cluster",
                "--name",
                CLUSTER_NAME,
                "--config",
                str(KIND_CONFIG),
            ]
        )
        created = True
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from k8s_cluster_cni import ensure_calico_cni, install_calico

    if created:
        install_calico()
    else:
        ensure_calico_cni(skip=skip_calico)


def kind_load_images() -> None:
    for tag in (IMAGE_API, IMAGE_MCP):
        print(f"Loading image into kind: {tag}")
        _run(["kind", "load", "docker-image", tag, "--name", CLUSTER_NAME])


def helm_value_files() -> list[str]:
    files = [
        HELM_CHART / "values.yaml",
        HELM_CHART / "values-dev.yaml",
        HELM_CHART / "values-minimal-dev.yaml",
    ]
    for path in files:
        if not path.is_file():
            raise SystemExit(f"Missing Helm values file: {path}")
    return [str(p) for p in files]


def helm_release_status() -> str | None:
    proc = _run(
        ["helm", "status", HELM_RELEASE, "-n", NAMESPACE, "-o", "json"],
        check=False,
        capture=True,
    )
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout or "{}").get("info", {}).get("status")


def ensure_helm_not_stuck() -> None:
    status = helm_release_status()
    if status in ("pending-install", "pending-upgrade", "pending-rollback", "failed"):
        print(
            f"Helm release {HELM_RELEASE!r} is {status!r}; uninstalling before retry..."
        )
        helm_uninstall()


def helm_upgrade_install() -> None:
    ensure_helm_not_stuck()
    cmd = [
        "helm",
        "upgrade",
        "--install",
        HELM_RELEASE,
        str(HELM_CHART),
        "--namespace",
        NAMESPACE,
        "--create-namespace",
        "--wait",
        "--timeout",
        "10m",
        "--set",
        f"secrets.postgresPassword={POSTGRES_PASSWORD}",
    ]
    for vf in helm_value_files():
        cmd.extend(["-f", vf])
    print("Running:", " ".join(cmd))
    _run(cmd)


def helm_uninstall() -> None:
    proc = _run(
        ["helm", "uninstall", HELM_RELEASE, "--namespace", NAMESPACE],
        check=False,
        capture=True,
    )
    if proc.returncode == 0:
        print(f"Removed Helm release {HELM_RELEASE!r} from {NAMESPACE}")
    else:
        print(f"Helm release {HELM_RELEASE!r} not found in {NAMESPACE} (ok)")


def wait_api_ready(timeout_seconds: int = 300) -> None:
    deadline = time.time() + timeout_seconds
    deployment = f"{HELM_RELEASE}-api"
    while time.time() < deadline:
        proc = _run(
            [
                "kubectl",
                "get",
                "deployment",
                deployment,
                "-n",
                NAMESPACE,
                "-o",
                "jsonpath={.status.availableReplicas}",
            ],
            check=False,
            capture=True,
        )
        if (proc.stdout or "").strip() == "1":
            print(f"Deployment {deployment} is available")
            return
        time.sleep(5)
    raise SystemExit(f"Timed out waiting for deployment/{deployment} in {NAMESPACE}")


def smoke_health(timeout_seconds: int = 30) -> None:
    pf = subprocess.Popen(
        [
            "kubectl",
            "port-forward",
            "-n",
            NAMESPACE,
            f"svc/{HELM_RELEASE}-api",
            f"{API_LOCAL_PORT}:8000",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        url = f"http://127.0.0.1:{API_LOCAL_PORT}/health"
        deadline = time.time() + timeout_seconds
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=3) as resp:
                    body = resp.read().decode("utf-8")
                    if resp.status == 200 and "ok" in body:
                        print(f"Smoke OK: {url} -> {body.strip()}")
                        return
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
            time.sleep(2)
        raise SystemExit(f"Smoke failed for {url}: {last_error}")
    finally:
        pf.terminate()
        try:
            pf.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pf.kill()


def cmd_status() -> None:
    require_tools("kubectl", "helm")
    _run(["kubectl", "get", "pods,svc", "-n", NAMESPACE], check=False)
    _run(["helm", "list", "-n", NAMESPACE], check=False)


def cmd_up(*, skip_build: bool, skip_smoke: bool, skip_calico: bool) -> None:
    require_tools("docker", "kind", "kubectl", "helm")
    if not KIND_CONFIG.is_file():
        raise SystemExit(f"Missing kind config: {KIND_CONFIG}")
    build_and_tag_images(skip_build=skip_build)
    ensure_kind_cluster(skip_calico=skip_calico)
    kind_load_images()
    helm_upgrade_install()
    wait_api_ready()
    if not skip_smoke:
        smoke_health()
    print(
        f"\nK8s stack up. Port-forward API:\n"
        f"  kubectl port-forward -n {NAMESPACE} svc/{HELM_RELEASE}-api 8000:8000"
    )


def cmd_down(*, keep_cluster: bool) -> None:
    require_tools("kind", "helm", "kubectl")
    helm_uninstall()
    if keep_cluster:
        print(f"Kept kind cluster {CLUSTER_NAME!r} (--keep-cluster)")
        return
    if kind_cluster_exists():
        _run(["kind", "delete", "cluster", "--name", CLUSTER_NAME])
        print(f"Deleted kind cluster {CLUSTER_NAME!r}")
    else:
        print(f"No kind cluster named {CLUSTER_NAME!r}")


def cmd_smoke() -> None:
    require_tools("kubectl")
    smoke_health()


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PS6.3 local kind + Helm helper")
    sub = p.add_subparsers(dest="command", required=True)

    up = sub.add_parser("up", help="Create cluster and install minimal dev chart")
    up.add_argument(
        "--skip-build", action="store_true", help="Skip docker compose build"
    )
    up.add_argument(
        "--skip-smoke", action="store_true", help="Skip /health smoke after install"
    )
    up.add_argument(
        "--skip-calico",
        action="store_true",
        help="Skip Calico CNI install (NetworkPolicy will not be enforced locally)",
    )

    down = sub.add_parser("down", help="Uninstall chart and delete kind cluster")
    down.add_argument(
        "--keep-cluster",
        action="store_true",
        help="Helm uninstall only; leave kind cluster running",
    )

    sub.add_parser("status", help="Show pods and helm release")
    sub.add_parser("smoke", help="Port-forward and GET /health")

    return p.parse_args()


def main() -> None:
    args = _parse_args()
    if args.command == "up":
        skip_calico = args.skip_calico or os.getenv("K8S_SKIP_CALICO", "").lower() in (
            "1",
            "true",
            "yes",
        )
        cmd_up(
            skip_build=args.skip_build,
            skip_smoke=args.skip_smoke,
            skip_calico=skip_calico,
        )
    elif args.command == "down":
        cmd_down(keep_cluster=args.keep_cluster)
    elif args.command == "status":
        cmd_status()
    elif args.command == "smoke":
        cmd_smoke()
    else:
        raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
