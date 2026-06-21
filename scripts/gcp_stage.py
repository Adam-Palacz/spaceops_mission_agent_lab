#!/usr/bin/env python3
"""GKE stage deploy smoke + portfolio E2E demo (PS6.8 / PS7.1)."""

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

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional for minimal envs

    def load_dotenv(*_args: object, **_kwargs: object) -> bool:
        return False


REPO_ROOT = Path(__file__).resolve().parent.parent
HELM_CHART = REPO_ROOT / "deploy" / "helm" / "spaceops"
OPS_CONFIG_KUSTOMIZE = REPO_ROOT / "deploy" / "gitops" / "ops-config-kustomize"
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
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    # Resolve bare tool names on Windows (gcloud.cmd, kubectl.exe, helm.exe).
    if cmd and "/" not in cmd[0] and "\\" not in cmd[0]:
        resolved = resolve_tool(cmd[0])
        cmd = [resolved, *cmd[1:]]
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture,
        cwd=cwd if cwd is not None else str(REPO_ROOT),
    )


def resolve_tool(name: str) -> str:
    """Full executable path (Windows: gcloud.cmd / kubectl.exe via shutil.which)."""
    path = shutil.which(name)
    if not path:
        raise SystemExit(
            f"Missing {name} on PATH. Run scripts/refresh_dev_path.ps1 or open a new terminal."
        )
    return path


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


def cluster_name() -> str:
    return os.getenv("GKE_CLUSTER_NAME", "spaceops-stage").strip()


def ensure_gke_credentials() -> None:
    """Refresh kubeconfig for the stage GKE cluster (fixes stale/unreachable API endpoint)."""
    project = PROJECT_ID or os.getenv("GCP_PROJECT_ID", "").strip()
    if not project:
        raise SystemExit("Set GCP_PROJECT_ID before deploy.")
    name = cluster_name()
    gcloud = resolve_tool("gcloud")

    describe = _run(
        [
            gcloud,
            "container",
            "clusters",
            "describe",
            name,
            "--region",
            REGION,
            "--project",
            project,
            "--format",
            "value(status)",
        ],
        check=False,
        capture=True,
    )
    if describe.returncode != 0:
        detail = (describe.stderr or describe.stdout or "").strip()
        raise SystemExit(
            f"No GKE cluster named {name!r} exists in {project}/{REGION}.\n\n"
            "Your kubeconfig may still point at an old, deleted control-plane endpoint; "
            "do not continue with Helm or secrets bootstrap until the cluster exists.\n\n"
            "Verify:\n"
            f"  gcloud container clusters list --project={project} --region={REGION}\n"
            "  cd infra/terraform/gcp\n"
            "  terraform state list\n"
            "  terraform plan\n\n"
            "Recover by either recreating/importing the stage cluster with Terraform or "
            "setting GKE_CLUSTER_NAME/GCP_REGION/GCP_PROJECT_ID to an existing cluster.\n\n"
            f"gcloud detail:\n{detail}"
        )

    status = (describe.stdout or "").strip()
    if status and status != "RUNNING":
        raise SystemExit(
            f"GKE cluster {name!r} exists in {project}/{REGION}, but status is {status!r}. "
            "Wait for it to become RUNNING before deploy."
        )

    print(f"Refreshing kubectl credentials for {name} ({project}/{REGION}) ...")
    creds = _run(
        [
            gcloud,
            "container",
            "clusters",
            "get-credentials",
            name,
            "--region",
            REGION,
            "--project",
            project,
        ],
        check=False,
        capture=True,
    )
    if creds.returncode != 0:
        detail = (creds.stderr or creds.stdout or "").strip()
        raise SystemExit(
            f"Failed to refresh kubectl credentials for {name!r} in {project}/{REGION}.\n\n"
            f"gcloud detail:\n{detail}"
        )


def preflight_kubectl() -> None:
    """Fail fast when the GKE API server is unreachable (auth expired, wrong context, cluster down)."""
    proc = _run(["kubectl", "cluster-info"], check=False, capture=True)
    if proc.returncode == 0:
        print((proc.stdout or "kubectl cluster-info OK").strip().splitlines()[0])
        return
    err = (proc.stderr or proc.stdout or "unknown error").strip()
    project = PROJECT_ID or os.getenv("GCP_PROJECT_ID", "YOUR_PROJECT")
    name = cluster_name()
    raise SystemExit(
        "kubectl cannot reach the Kubernetes API (GKE control plane).\n\n"
        "Typical fixes:\n"
        "  1. gcloud auth login\n"
        "  2. gcloud auth application-default login\n"
        f"  3. gcloud container clusters get-credentials {name} "
        f"--region {REGION} --project {project}\n"
        "  4. make gcp-kube-credentials   (from repo root; sets GCP_PROJECT_ID)\n\n"
        "If the cluster was deleted, re-run terraform apply or use a live cluster endpoint.\n"
        "Check current context: kubectl config current-context\n\n"
        f"kubectl detail:\n{err}"
    )


def helm_value_files(*, full_stack: bool, monitoring: bool) -> list[Path]:
    files = [
        HELM_CHART / "values.yaml",
        HELM_CHART / "values-stage.yaml",
        HELM_CHART / "values-gcp-stage.yaml",
    ]
    if full_stack:
        files.insert(2, HELM_CHART / "values-stage-full.yaml")
        files.insert(3, HELM_CHART / "values-ops-config-mounts.yaml")
    if monitoring:
        files.insert(-1, HELM_CHART / "values-monitoring-stage.yaml")
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


def cmd_teardown(
    *,
    confirm: bool,
    skip_helm: bool,
    skip_terraform: bool,
    skip_argocd: bool,
    terraform_auto_approve: bool,
    destroy_budget_alert: bool,
) -> None:
    """Remove stage resources, preserving the billing alert unless explicitly requested."""
    if not confirm:
        raise SystemExit(
            "Refusing teardown without --confirm (deletes stage workloads and Terraform resources)."
        )

    project = PROJECT_ID or os.getenv("GCP_PROJECT_ID", "").strip()
    tf_dir = REPO_ROOT / "infra" / "terraform" / "gcp"

    if not skip_helm:
        require_tools("kubectl", "helm", "gcloud")
        load_repo_dotenv()
        try:
            ensure_gke_credentials()
        except SystemExit:
            print(
                "Warning: could not refresh GKE credentials; continuing with current kubeconfig."
            )
        print(f"Helm uninstall {HELM_RELEASE} in {NAMESPACE} ...")
        _run(
            ["helm", "uninstall", HELM_RELEASE, "-n", NAMESPACE],
            check=False,
        )
        print(f"Delete namespace {NAMESPACE} ...")
        _run(
            [
                "kubectl",
                "delete",
                "namespace",
                NAMESPACE,
                "--ignore-not-found",
                "--wait=false",
            ],
            check=False,
        )
        if not skip_argocd:
            print("Delete namespace argocd (if present) ...")
            _run(
                [
                    "kubectl",
                    "delete",
                    "namespace",
                    "argocd",
                    "--ignore-not-found",
                    "--wait=false",
                ],
                check=False,
            )
    else:
        print("Skipped Helm / namespace cleanup (--skip-helm).")

    if not skip_terraform:
        require_tools("terraform")
        if not tf_dir.is_dir():
            raise SystemExit(f"Missing Terraform directory: {tf_dir}")
        print(f"Terraform destroy in {tf_dir} ...")
        init = _run(
            ["terraform", "init"],
            check=False,
            capture=True,
            cwd=str(tf_dir),
        )
        if init.returncode != 0:
            raise SystemExit(init.stderr.strip() or "terraform init failed")
        destroy_cmd = ["terraform", "destroy"]
        if terraform_auto_approve:
            destroy_cmd.append("-auto-approve")
        else:
            print("Terraform will prompt for confirmation (type 'yes').")
        proc = subprocess.run(
            destroy_cmd,
            cwd=str(tf_dir),
            check=False,
        )
        if proc.returncode != 0:
            raise SystemExit(
                "terraform destroy failed or was cancelled. "
                "Fix errors or delete remaining resources in GCP Console."
            )
        if not destroy_budget_alert:
            print("Restoring persistent billing budget alert (if enabled) ...")
            apply_cmd = [
                "terraform",
                "apply",
                "-target=google_billing_budget.spaceops",
            ]
            if terraform_auto_approve:
                apply_cmd.append("-auto-approve")
            else:
                print("Terraform will prompt to restore the budget alert (type 'yes').")
            proc = subprocess.run(
                apply_cmd,
                cwd=str(tf_dir),
                check=False,
            )
            if proc.returncode != 0:
                raise SystemExit(
                    "Stage resources were destroyed, but restoring the persistent budget "
                    "alert failed. Run terraform apply "
                    "-target=google_billing_budget.spaceops from infra/terraform/gcp."
                )
    else:
        print("Skipped Terraform destroy (--skip-terraform).")

    print("\n--- Teardown complete (verify in GCP Console) ---")
    if project:
        gcloud = resolve_tool("gcloud")
        print("\nClusters:")
        subprocess.run(
            [
                gcloud,
                "container",
                "clusters",
                "list",
                "--project",
                project,
                f"--filter=location:{REGION}",
            ],
            check=False,
        )
        print("\nArtifact Registry repos:")
        subprocess.run(
            [
                gcloud,
                "artifacts",
                "repositories",
                "list",
                "--project",
                project,
                "--location",
                REGION,
            ],
            check=False,
        )
    print(
        "\nIf a GKE cluster still exists but was never in Terraform state, delete it manually:\n"
        f"  gcloud container clusters delete {cluster_name()} --region {REGION} --project <project>\n"
        "Optional: delete the entire GCP project when the trial ends."
    )


def load_repo_dotenv() -> None:
    """Load .env from repo root when POSTGRES_PASSWORD / OPENAI_API_KEY are unset."""
    env_path = REPO_ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)


def run_kb_index() -> None:
    """Populate pgvector chunks for KB MCP (required for portfolio scenario A citations)."""
    print("Indexing KB (kubectl exec spaceops-kb-mcp) ...")
    proc = _run(
        [
            "kubectl",
            "exec",
            "-n",
            NAMESPACE,
            f"deploy/{HELM_RELEASE}-kb-mcp",
            "--",
            "python",
            "-m",
            "apps.mcp.kb_server.index_kb",
        ],
        check=False,
        capture=True,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise SystemExit(f"KB index failed: {err or 'index_kb exit non-zero'}")
    print((proc.stdout or "index_kb OK").strip())


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


def apply_ops_config() -> None:
    """Apply the ops-config ConfigMap required by stage-full mounts."""
    if not OPS_CONFIG_KUSTOMIZE.is_dir():
        raise SystemExit(f"Missing ops-config kustomize dir: {OPS_CONFIG_KUSTOMIZE}")
    print("Applying ops-config ConfigMap ...")
    _run(["kubectl", "apply", "-k", str(OPS_CONFIG_KUSTOMIZE)])


def cmd_deploy(
    *,
    full_stack: bool,
    monitoring: bool,
    skip_secrets: bool,
    skip_migrate: bool,
    skip_kb_index: bool,
    skip_kube_refresh: bool,
    wait_timeout: str,
) -> None:
    require_tools("kubectl", "helm", "gcloud")
    load_repo_dotenv()
    if not skip_kube_refresh:
        ensure_gke_credentials()
    preflight_kubectl()
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
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "k8s_secrets_bootstrap.py"),
                "--create-namespace",
            ],
            check=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        if monitoring:
            password = os.getenv("GRAFANA_ADMIN_PASSWORD", "spaceops-stage-admin")
            print("Creating/updating Grafana admin Secret for monitoring overlay ...")
            secret_yaml = subprocess.run(
                [
                    resolve_tool("kubectl"),
                    "create",
                    "secret",
                    "generic",
                    "spaceops-stage-monitoring-secrets",
                    "-n",
                    NAMESPACE,
                    f"--from-literal=grafana-admin-password={password}",
                    "--dry-run=client",
                    "-o",
                    "yaml",
                ],
                check=True,
                text=True,
                capture_output=True,
                cwd=str(REPO_ROOT),
            )
            subprocess.run(
                [resolve_tool("kubectl"), "apply", "-f", "-"],
                input=secret_yaml.stdout,
                check=True,
                text=True,
                cwd=str(REPO_ROOT),
            )

    apply_ops_config()

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
    for vf in helm_value_files(full_stack=full_stack, monitoring=monitoring):
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
    if full_stack and not skip_kb_index:
        run_kb_index()
    base = resolve_api_base_url(None)
    print(f"\nDeploy complete. API: {base}/health")


def smoke_health(base_url: str) -> None:
    status, body = http_json("GET", f"{base_url}/health", timeout=30.0)
    if status != 200 or body.get("status") != "ok":
        raise SystemExit(f"Health check failed: HTTP {status} {body}")
    print(f"Smoke OK: {base_url}/health -> {body}")


def cmd_smoke(api_url: str | None, *, skip_kube_refresh: bool) -> None:
    require_tools("kubectl", "gcloud")
    if not skip_kube_refresh:
        ensure_gke_credentials()
    preflight_kubectl()
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


def validate_scenario_a(body: dict) -> None:
    """Portfolio scenario A: structured report (citations optional on GKE)."""
    report = body.get("report") or {}
    if not report.get("executive_summary"):
        raise SystemExit("Scenario A failed: missing report.executive_summary")
    if not report.get("evidence"):
        raise SystemExit("Scenario A failed: missing report.evidence")
    cites = report.get("citation_refs") or []
    if cites:
        print(f"Scenario A PASS: report + {len(cites)} citation_ref(s)")
    else:
        print(
            "Scenario A PASS: report + evidence (no citations — re-run deploy with "
            "full stack + index_kb, or rebuild images after PS7.1 dockerignore fix)"
        )


def validate_scenario_b(body: dict) -> None:
    """Portfolio scenario B: must escalate (no_evidence or similar)."""
    report = body.get("report") or {}
    packet = report.get("escalation_packet") or {}
    escalated = bool(packet or body.get("escalated"))
    if not escalated:
        raise SystemExit(
            "Scenario B failed: expected escalation_packet or escalated=true"
        )
    reason = packet.get("reason", "unknown")
    print(f"Scenario B PASS: escalated (reason={reason})")


def cmd_demo(
    api_url: str | None,
    *,
    skip_ingest: bool,
    scenario: str,
    skip_wait: bool,
    skip_kube_refresh: bool,
) -> None:
    require_tools("kubectl", "gcloud")
    if not skip_kube_refresh:
        ensure_gke_credentials()
    preflight_kubectl()
    base = resolve_api_base_url(api_url)
    smoke_health(base)

    if not skip_ingest:
        ingest_telemetry(base)
        if not skip_wait:
            print(f"Waiting {PERSISTER_WAIT_SECONDS}s for telemetry-persister ...")
            time.sleep(PERSISTER_WAIT_SECONDS)

    if scenario in ("a", "both"):
        body_a = run_scenario(base, SCENARIO_A)
        validate_scenario_a(body_a)
    if scenario in ("b", "both"):
        body_b = run_scenario(base, SCENARIO_B)
        validate_scenario_b(body_b)

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
    p_deploy.add_argument(
        "--monitoring",
        action="store_true",
        help="Include PR1.1 values-monitoring-stage.yaml and Grafana admin Secret.",
    )
    p_deploy.add_argument("--skip-secrets", action="store_true")
    p_deploy.add_argument(
        "--skip-migrate",
        action="store_true",
        help="Skip Alembic upgrade head via API pod",
    )
    p_deploy.add_argument(
        "--skip-kb-index",
        action="store_true",
        help="Skip KB index_kb after migrations (full stack only)",
    )
    p_deploy.add_argument("--timeout", default="15m")
    p_deploy.add_argument(
        "--skip-kube-refresh",
        action="store_true",
        help="Skip gcloud get-credentials (use current kubeconfig as-is)",
    )

    p_smoke = sub.add_parser("smoke", help="GET /health via LoadBalancer")
    p_smoke.add_argument("--api-url", default=None)
    p_smoke.add_argument("--skip-kube-refresh", action="store_true")

    p_demo = sub.add_parser("demo", help="Ingest + portfolio scenarios A/B")
    p_demo.add_argument("--api-url", default=None)
    p_demo.add_argument("--skip-ingest", action="store_true")
    p_demo.add_argument("--skip-wait", action="store_true")
    p_demo.add_argument(
        "--scenario",
        choices=("a", "b", "both"),
        default="both",
    )
    p_demo.add_argument("--skip-kube-refresh", action="store_true")

    p_kube = sub.add_parser(
        "kube-credentials",
        help="gcloud get-credentials for stage GKE (no Helm deploy)",
    )
    p_kube.add_argument("--skip-preflight", action="store_true")

    sub.add_parser("status", help="kubectl get pods/svc + helm list")

    p_teardown = sub.add_parser(
        "teardown",
        help="Helm uninstall + namespace delete + terraform destroy (lab shutdown)",
    )
    p_teardown.add_argument(
        "--confirm",
        action="store_true",
        help="Required. Irreversibly removes stage resources.",
    )
    p_teardown.add_argument("--skip-helm", action="store_true")
    p_teardown.add_argument("--skip-terraform", action="store_true")
    p_teardown.add_argument("--skip-argocd", action="store_true")
    p_teardown.add_argument(
        "--terraform-auto-approve",
        action="store_true",
        help="Pass -auto-approve to terraform destroy (non-interactive).",
    )
    p_teardown.add_argument(
        "--destroy-budget-alert",
        action="store_true",
        help="Also remove the billing budget alert; default teardown restores it.",
    )

    args = parser.parse_args()

    if args.command == "deploy":
        cmd_deploy(
            full_stack=not args.minimal,
            monitoring=args.monitoring,
            skip_secrets=args.skip_secrets,
            skip_migrate=args.skip_migrate,
            skip_kb_index=args.skip_kb_index,
            skip_kube_refresh=args.skip_kube_refresh,
            wait_timeout=args.timeout,
        )
    elif args.command == "smoke":
        cmd_smoke(args.api_url, skip_kube_refresh=args.skip_kube_refresh)
    elif args.command == "demo":
        cmd_demo(
            args.api_url,
            skip_ingest=args.skip_ingest,
            scenario=args.scenario,
            skip_wait=args.skip_wait,
            skip_kube_refresh=args.skip_kube_refresh,
        )
    elif args.command == "kube-credentials":
        require_tools("gcloud")
        load_repo_dotenv()
        ensure_gke_credentials()
        if not args.skip_preflight:
            preflight_kubectl()
    elif args.command == "status":
        cmd_status()
    elif args.command == "teardown":
        cmd_teardown(
            confirm=args.confirm,
            skip_helm=args.skip_helm,
            skip_terraform=args.skip_terraform,
            skip_argocd=args.skip_argocd,
            terraform_auto_approve=args.terraform_auto_approve,
            destroy_budget_alert=args.destroy_budget_alert,
        )
    else:
        raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
