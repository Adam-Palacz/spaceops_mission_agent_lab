#!/usr/bin/env python3
"""PS6.11 local kind gate: enable checkpoint, kill api pod, resume (manual / --execute)."""

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
HELM_CHART = REPO_ROOT / "deploy" / "helm" / "spaceops"
NAMESPACE = os.getenv("K8S_NAMESPACE", "spaceops-dev")
HELM_RELEASE = os.getenv("K8S_HELM_RELEASE", "spaceops")
API_LOCAL_PORT = int(os.getenv("K8S_API_LOCAL_PORT", "18000"))
POSTGRES_PASSWORD = os.getenv("K8S_POSTGRES_PASSWORD", "spaceops")
INCIDENT_ID = os.getenv("K8S_CHECKPOINT_INCIDENT_ID", "ckpt-oom-test")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="PS6.11 checkpoint OOM/resume demo on local kind."
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="Run helm upgrade, POST /runs, delete api pod, POST /runs/resume.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned steps only (default when --execute omitted).",
    )
    return p.parse_args()


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=check, text=True, cwd=str(REPO_ROOT))


def _helm_upgrade() -> None:
    files = [
        "values.yaml",
        "values-dev.yaml",
        "values-minimal-dev.yaml",
        "values-checkpoint-dev.yaml",
    ]
    cmd = [
        "helm",
        "upgrade",
        HELM_RELEASE,
        str(HELM_CHART),
        "--namespace",
        NAMESPACE,
        "--wait",
        "--timeout",
        "5m",
        "--set",
        f"secrets.postgresPassword={POSTGRES_PASSWORD}",
    ]
    for vf in files:
        cmd.extend(["-f", str(HELM_CHART / vf)])
    _run(cmd)


def _api_post(path: str, body: dict) -> dict:
    url = f"http://127.0.0.1:{API_LOCAL_PORT}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _port_forward() -> subprocess.Popen[str]:
    cmd = [
        "kubectl",
        "port-forward",
        f"svc/{HELM_RELEASE}-api",
        "-n",
        NAMESPACE,
        f"{API_LOCAL_PORT}:8000",
    ]
    print("+", " ".join(cmd), "(background)")
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _wait_api() -> None:
    url = f"http://127.0.0.1:{API_LOCAL_PORT}/health"
    for _ in range(30):
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
    raise SystemExit("API health check failed — is make k8s-up done?")


def main() -> int:
    args = _parse_args()
    dry = args.dry_run or not args.execute

    steps = [
        "helm upgrade with values-checkpoint-dev.yaml (AGENT_DURABLE_CHECKPOINT_ENABLED=true)",
        f"kubectl port-forward svc/{HELM_RELEASE}-api -n {NAMESPACE} {API_LOCAL_PORT}:8000",
        f"POST /runs incident_id={INCIDENT_ID} (capture run_id)",
        f"kubectl delete pod -l app.kubernetes.io/component=api -n {NAMESPACE}",
        "kubectl wait for api Ready",
        "POST /runs/resume with same run_id",
    ]
    print("PS6.11 checkpoint demo (Variant B — api Deployment)")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
    if dry:
        print(
            "mode=dry-run (pass --execute to run; requires make k8s-up + OPENAI_API_KEY in secret)"
        )
        return 0

    for tool in ("helm", "kubectl"):
        if not shutil.which(tool):
            raise SystemExit(f"Missing {tool} on PATH")

    _helm_upgrade()
    pf = _port_forward()
    try:
        _wait_api()
        run_body = {
            "incident_id": INCIDENT_ID,
            "payload": {
                "time_range_start": "2025-02-14T09:00:00Z",
                "time_range_end": "2025-02-14T11:00:00Z",
                "message": "checkpoint oom test",
            },
        }
        started = _api_post("/runs", run_body)
        run_id = started.get("run_id") or started.get("id")
        print(f"started run_id={run_id!r}")
        _run(
            [
                "kubectl",
                "delete",
                "pod",
                "-n",
                NAMESPACE,
                "-l",
                "app.kubernetes.io/component=api",
                "--wait=false",
            ]
        )
        _run(
            [
                "kubectl",
                "wait",
                "--for=condition=Ready",
                "pod",
                "-l",
                "app.kubernetes.io/component=api",
                "-n",
                NAMESPACE,
                "--timeout=120s",
            ]
        )
        time.sleep(2)
        _wait_api()
        if not run_id:
            raise SystemExit("No run_id in POST /runs response — cannot resume")
        resumed = _api_post(
            "/runs/resume",
            {"run_id": run_id, "incident_id": INCIDENT_ID, "payload": {}},
        )
        print(json.dumps(resumed, indent=2)[:2000])
        status = resumed.get("status", "")
        if status not in ("resumed", "completed") and not resumed.get("report"):
            raise SystemExit(f"Unexpected resume outcome: {status!r}")
        print("PS6.11 gate: OK")
        return 0
    finally:
        pf.terminate()
        pf.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
