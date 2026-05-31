#!/usr/bin/env python3
"""GKE stage deploy smoke + portfolio E2E demo (PS6.8 stretch)."""

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
TELEMETRY_FIXTURE = REPO_ROOT / "data" / "telemetry" / "telemetry.ndjson"
HELM_RELEASE = os.getenv("GCP_HELM_RELEASE", "spaceops")
NAMESPACE = os.getenv("K8S_NAMESPACE", "spaceops-stage")
REGION = os.getenv("GCP_REGION", "us-central1")
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "").strip()
IMAGE_TAG = os.getenv("GCP_IMAGE_TAG", "stage")
API_PORT = int(os.getenv("GCP_API_PORT", "8000"))
PERSISTER_WAIT_SECONDS = int(os.getenv("GCP_PERSISTER_WAIT_SECONDS", "20"))

SCENARIO_A = {
    "incident_id": "gcp-scenario-a",
    "payload": {
        "time_range_start": "2025-02-14T09:00:00Z",
        "time_range_end": "2025-02-14T11:00:00Z",
        "message": "power bus voltage anomaly",
        "channels": ["bus_voltage"],
    },
}

SCENARIO_B = {
    "incident_id": "gcp-scenario-b",
    "payload": {
        "time_range_start": "2025-02-14T09:00:00Z",
        "time_range_end": "2025-02-14T09:00:01Z",
        "ref": "no-data",
    },
}


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


def artifact_registry_base() -> str:
    if not PROJECT_ID:
        raise SystemExit(
            "Set GCP_PROJECT_ID (e.g. spaceops-project) for deploy/upgrade."
        )
    return f"{REGION}-docker.pkg.dev/{PROJECT_ID}/spaceops"


def helm_value_files(*, full_stack: bool) -> list[Path]:
    files = [
        HELM_CHART / "values.yaml",
        HELM_CHART / "values-stage.yaml",
        HELM_CHART / "values-gcp-stage.yaml",
    ]
    if full_stack:
        files.insert(2, HELM_CHART / "values-stage-full.yaml")
    for path in files:
        if not path.is_file():
            raise SystemExit(f"Missing Helm values: {path}")
    return files


def resolve_api_base_url(explicit: str | None) -> str:
    if explicit:
        return explicit.rstrip("/")
    env = os.getenv("GCP_API_URL", "").strip().rstrip("/")
    if env:
        return env
    proc = _run(
        [
            "kubectl",
            "get",
            "svc",
            f"{HELM_RELEASE}-api",
            "-n",
            NAMESPACE,
            "-o",
            "jsonpath={.status.loadBalancer.ingress[0].ip}",
        ],
        capture=True,
    )
    ip = (proc.stdout or "").strip()
    if not ip:
        raise SystemExit(
            "LoadBalancer IP not ready. Set GCP_API_URL or wait for spaceops-api EXTERNAL-IP."
        )
    return f"http://{ip}:{API_PORT}"


def http_json(
    method: str,
    url: str,
    *,
    body: dict | None = None,
    raw_body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> tuple[int, dict]:
    hdrs = dict(headers or {})
    data: bytes | None = raw_body
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
            return resp.status, json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(detail)
        except json.JSONDecodeError:
            payload = {"detail": detail}
        return exc.code, payload


def cmd_status() -> None:
    require_tools("kubectl", "helm")
    _run(["kubectl", "get", "pods,svc", "-n", NAMESPACE], check=False)
    _run(["helm", "list", "-n", NAMESPACE], check=False)


def run_db_migrations() -> None:
    """Apply Alembic schema (telemetry + dlq_events) via API pod."""
    print("Running Alembic migrations (kubectl exec spaceops-api) ...")
    proc = _run(
        [
            "kubectl",
            "exec",
            "-n",
            NAMESPACE,
            f"deploy/{HELM_RELEASE}-api",
            "--",
            "python",
            "-m",
            "alembic",
            "upgrade",
            "head",
        ],
        check=False,
        capture=True,
    )
    if proc.returncode != 0:
        raise SystemExit(
            proc.stderr.strip() or proc.stdout.strip() or "alembic upgrade failed"
        )
    print((proc.stdout or proc.stderr or "alembic upgrade head OK").strip())


def cmd_deploy(
    *, full_stack: bool, skip_secrets: bool, skip_migrate: bool, wait_timeout: str
) -> None:
    require_tools("kubectl", "helm")
    ar = artifact_registry_base()

    if not skip_secrets:
        require_tools("python")
        if not os.getenv("POSTGRES_PASSWORD") or not os.getenv("OPENAI_API_KEY"):
            raise SystemExit(
                "Export POSTGRES_PASSWORD and OPENAI_API_KEY (or load from .env) before deploy."
            )
        env = os.environ.copy()
        env["K8S_NAMESPACE"] = NAMESPACE
        env["K8S_SECRET_NAME"] = os.getenv("K8S_SECRET_NAME", "spaceops-stage-secrets")
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "k8s_secrets_bootstrap.py")],
            check=True,
            cwd=str(REPO_ROOT),
            env=env,
        )

    ns_proc = _run(
        ["kubectl", "create", "namespace", NAMESPACE],
        check=False,
        capture=True,
    )
    if ns_proc.returncode not in (0, 1) or (
        ns_proc.returncode == 1 and "AlreadyExists" not in (ns_proc.stderr or "")
    ):
        raise SystemExit(ns_proc.stderr.strip() or "kubectl create namespace failed")

    cmd = [
        "helm",
        "upgrade",
        "--install",
        HELM_RELEASE,
        str(HELM_CHART),
        "--namespace",
        NAMESPACE,
        "--set",
        "global.createNamespace=false",
        "--set",
        f"images.api.repository={ar}/api",
        "--set",
        f"images.mcp.repository={ar}/mcp",
        "--set",
        f"images.api.tag={IMAGE_TAG}",
        "--set",
        f"images.mcp.tag={IMAGE_TAG}",
        "--wait",
        "--timeout",
        wait_timeout,
    ]
    for vf in helm_value_files(full_stack=full_stack):
        cmd.extend(["-f", str(vf)])

    print("Running:", " ".join(cmd))
    _run(cmd)
    if not skip_migrate:
        run_db_migrations()
        _run(
            [
                "kubectl",
                "rollout",
                "restart",
                f"deploy/{HELM_RELEASE}-telemetry-persister",
                "-n",
                NAMESPACE,
            ]
        )
        _run(
            [
                "kubectl",
                "rollout",
                "status",
                f"deploy/{HELM_RELEASE}-telemetry-persister",
                "-n",
                NAMESPACE,
                "--timeout",
                "3m",
            ]
        )
    base = resolve_api_base_url(None)
    print(f"\nDeploy complete. API: {base}/health")


def smoke_health(base_url: str) -> None:
    status, body = http_json("GET", f"{base_url}/health", timeout=30.0)
    if status != 200 or body.get("status") != "ok":
        raise SystemExit(f"Health check failed: HTTP {status} {body}")
    print(f"Smoke OK: {base_url}/health -> {body}")


def cmd_smoke(api_url: str | None) -> None:
    require_tools("kubectl")
    base = resolve_api_base_url(api_url)
    smoke_health(base)


def ingest_telemetry(base_url: str) -> dict:
    if not TELEMETRY_FIXTURE.is_file():
        raise SystemExit(f"Missing fixture: {TELEMETRY_FIXTURE}")
    raw = TELEMETRY_FIXTURE.read_bytes()
    status, body = http_json(
        "POST",
        f"{base_url}/ingest?source=telemetry",
        raw_body=raw,
        headers={"Content-Type": "application/x-ndjson"},
        timeout=60.0,
    )
    if status not in (200, 202):
        raise SystemExit(f"Ingest failed: HTTP {status} {body}")
    print(f"Ingest OK: {body}")
    return body


def run_scenario(base_url: str, payload: dict) -> dict:
    print(f"POST /runs incident_id={payload['incident_id']!r} ...")
    status, body = http_json("POST", f"{base_url}/runs", body=payload, timeout=180.0)
    if status != 200:
        raise SystemExit(f"Run failed: HTTP {status} {body}")
    report = body.get("report") or {}
    escalated = bool((report.get("escalation_packet") or body.get("escalated")))
    print(
        f"Run OK: status={body.get('status')} run_id={body.get('run_id')} "
        f"escalated={escalated}"
    )
    trace = (report.get("trace_link") or "").strip()
    if trace:
        print(f"  trace_link (Jaeger after port-forward): {trace}")
    return body


def cmd_demo(
    api_url: str | None,
    *,
    skip_ingest: bool,
    scenario: str,
    skip_wait: bool,
) -> None:
    require_tools("kubectl")
    base = resolve_api_base_url(api_url)
    smoke_health(base)

    if not skip_ingest:
        ingest_telemetry(base)
        if not skip_wait:
            print(f"Waiting {PERSISTER_WAIT_SECONDS}s for telemetry-persister ...")
            time.sleep(PERSISTER_WAIT_SECONDS)

    if scenario in ("a", "both"):
        run_scenario(base, SCENARIO_A)
    if scenario in ("b", "both"):
        run_scenario(base, SCENARIO_B)

    print(
        "\nLive observability:\n"
        f"  kubectl logs -n {NAMESPACE} -l app.kubernetes.io/component=api -f\n"
        f"  kubectl port-forward -n {NAMESPACE} svc/{HELM_RELEASE}-jaeger 16686:16686\n"
        f"  Jaeger UI: http://localhost:16686 (service spaceops-api)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="GKE stage deploy and E2E demo")
    sub = parser.add_subparsers(dest="command", required=True)

    p_deploy = sub.add_parser(
        "deploy", help="Helm upgrade --install full GKE stage stack"
    )
    p_deploy.add_argument(
        "--minimal",
        action="store_true",
        help="Skip values-stage-full.yaml (telemetry MCP only)",
    )
    p_deploy.add_argument("--skip-secrets", action="store_true")
    p_deploy.add_argument(
        "--skip-migrate",
        action="store_true",
        help="Skip Alembic upgrade head via API pod",
    )
    p_deploy.add_argument("--timeout", default="15m")

    p_smoke = sub.add_parser("smoke", help="GET /health via LoadBalancer")
    p_smoke.add_argument("--api-url", default=None)

    p_demo = sub.add_parser("demo", help="Ingest + portfolio scenarios A/B")
    p_demo.add_argument("--api-url", default=None)
    p_demo.add_argument("--skip-ingest", action="store_true")
    p_demo.add_argument("--skip-wait", action="store_true")
    p_demo.add_argument(
        "--scenario",
        choices=("a", "b", "both"),
        default="both",
    )

    sub.add_parser("status", help="kubectl get pods/svc + helm list")

    args = parser.parse_args()

    if args.command == "deploy":
        cmd_deploy(
            full_stack=not args.minimal,
            skip_secrets=args.skip_secrets,
            skip_migrate=args.skip_migrate,
            wait_timeout=args.timeout,
        )
    elif args.command == "smoke":
        cmd_smoke(args.api_url)
    elif args.command == "demo":
        cmd_demo(
            args.api_url,
            skip_ingest=args.skip_ingest,
            scenario=args.scenario,
            skip_wait=args.skip_wait,
        )
    elif args.command == "status":
        cmd_status()
    else:
        raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
