#!/usr/bin/env python3
"""PS6.4 local Helm rollout + rollback demonstration (requires `make k8s-up` first)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HELM_CHART = REPO_ROOT / "deploy" / "helm" / "spaceops"
CLUSTER_NAME = os.getenv("K8S_CLUSTER_NAME", "spaceops-dev")
HELM_RELEASE = os.getenv("K8S_HELM_RELEASE", "spaceops")
NAMESPACE = os.getenv("K8S_NAMESPACE", "spaceops-dev")
API_LOCAL_PORT = int(os.getenv("K8S_API_LOCAL_PORT", "18000"))
POSTGRES_PASSWORD = os.getenv("K8S_POSTGRES_PASSWORD", "spaceops")
API_DEPLOYMENT = f"{HELM_RELEASE}-api"


def _run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture,
        cwd=str(REPO_ROOT),
    )


def require_tools(*tools: str) -> None:
    missing = [t for t in tools if not shutil.which(t)]
    if missing:
        raise SystemExit(f"Missing required tools on PATH: {', '.join(missing)}")


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


def helm_latest_revision() -> int:
    proc = _run(
        ["helm", "history", HELM_RELEASE, "-n", NAMESPACE, "-o", "json"],
        capture=True,
    )
    history = json.loads(proc.stdout or "[]")
    if not history:
        raise SystemExit(f"No Helm history for {HELM_RELEASE!r} in {NAMESPACE}")
    return max(int(row["revision"]) for row in history)


def helm_upgrade(*extra_set: str) -> int:
    cmd = [
        "helm",
        "upgrade",
        HELM_RELEASE,
        str(HELM_CHART),
        "--namespace",
        NAMESPACE,
        "--atomic",
        "--wait",
        "--timeout",
        "10m",
        "--set",
        f"secrets.postgresPassword={POSTGRES_PASSWORD}",
        *extra_set,
    ]
    for vf in helm_value_files():
        cmd.extend(["-f", vf])
    print("Running:", " ".join(cmd))
    _run(cmd)
    return helm_latest_revision()


def helm_rollback(revision: int) -> None:
    print(f"Rolling back {HELM_RELEASE!r} to revision {revision}...")
    _run(
        [
            "helm",
            "rollback",
            HELM_RELEASE,
            str(revision),
            "--namespace",
            NAMESPACE,
            "--wait",
            "--timeout",
            "10m",
        ]
    )


def api_llm_backend() -> str:
    proc = _run(
        [
            "kubectl",
            "get",
            "deployment",
            API_DEPLOYMENT,
            "-n",
            NAMESPACE,
            "-o",
            'jsonpath={.spec.template.spec.containers[0].env[?(@.name=="LLM_BACKEND")].value}',
        ],
        capture=True,
    )
    return (proc.stdout or "").strip()


def smoke_health() -> None:
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
        with urllib.request.urlopen(url, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            if resp.status != 200 or "ok" not in body:
                raise SystemExit(f"Smoke failed: {url} -> {body!r}")
            print(f"Smoke OK: {url} -> {body.strip()}")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SystemExit(f"Smoke failed for /health: {exc}") from exc
    finally:
        pf.terminate()
        try:
            pf.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pf.kill()


def pre_checks() -> None:
    require_tools("kubectl", "helm", "kind")
    ctx = _run(["kubectl", "config", "current-context"], capture=True)
    print(f"kubectl context: {(ctx.stdout or '').strip()}")
    clusters = _run(["kind", "get", "clusters"], capture=True)
    if CLUSTER_NAME not in (clusters.stdout or "").split():
        raise SystemExit(
            f"kind cluster {CLUSTER_NAME!r} not found — run `make k8s-up` first"
        )
    status = _run(
        ["helm", "status", HELM_RELEASE, "-n", NAMESPACE],
        check=False,
        capture=True,
    )
    if status.returncode != 0:
        raise SystemExit(
            f"Helm release {HELM_RELEASE!r} not installed in {NAMESPACE} — run `make k8s-up`"
        )


def demo_revision_rollback() -> None:
    print("\n=== Part A: deploy marker v2 -> helm rollback -> /health ===")
    baseline_rev = helm_latest_revision()
    print(f"Baseline revision: {baseline_rev}")
    smoke_health()

    helm_upgrade("--set", "api.extraEnv.DEMO_ROLLOUT_VERSION=v2")
    bad_rev = helm_latest_revision()
    print(f"Upgraded to revision {bad_rev} (demo marker v2)")

    helm_rollback(baseline_rev)
    print(f"Rolled back to revision {baseline_rev}")
    smoke_health()
    print("Part A passed.")


def demo_llm_emergency_rollback() -> None:
    print("\n=== Part B: bad LLM_BACKEND=gpu -> patch openai ===")
    before = api_llm_backend()
    print(f"LLM_BACKEND before: {before!r}")

    helm_upgrade("--set", "api.llm.backend=gpu")
    gpu_backend = api_llm_backend()
    print(f"LLM_BACKEND after bad deploy: {gpu_backend!r}")
    if gpu_backend != "gpu":
        raise SystemExit("Expected LLM_BACKEND=gpu after simulated bad deploy")

    helm_upgrade("--set", "api.llm.backend=openai", "--set", "nim.enabled=false")
    restored = api_llm_backend()
    print(f"LLM_BACKEND after emergency patch: {restored!r}")
    if restored != "openai":
        raise SystemExit("Emergency rollback failed: LLM_BACKEND is not openai")

    smoke_health()
    print("Part B passed (config-only LLM rollback; /health OK).")
    print(
        "Optional: POST /runs with OPENAI_API_KEY in Secret — "
        "see docs/runbooks/k8s_rollout_rollback.md"
    )


def run_demo(*, skip_llm: bool) -> None:
    pre_checks()
    demo_revision_rollback()
    if not skip_llm:
        demo_llm_emergency_rollback()
    print("\nPS6.4 rollout demo complete.")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PS6.4 Helm rollout/rollback local demo")
    p.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip Part B (LLM emergency rollback simulation)",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        run_demo(skip_llm=args.skip_llm)
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc.stdout or str(exc), file=sys.stderr)
        raise SystemExit(exc.returncode) from exc


if __name__ == "__main__":
    main()
