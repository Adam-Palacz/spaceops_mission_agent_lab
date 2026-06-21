"""PR1.1 — K8s monitoring stack Helm and roadmap tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CHART = REPO_ROOT / "deploy" / "helm" / "spaceops"
PR11 = (
    REPO_ROOT
    / "roadmap"
    / "02.5-production-readiness"
    / "sprint-1"
    / "PR1.1-k8s-monitoring-stack.md"
)
BOARD = REPO_ROOT / "roadmap" / "02.5-production-readiness" / "sprint-1" / "BOARD.md"
HELM_README = CHART / "README.md"
GCP_RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "gcp_stage_deploy.md"


def _helm_available() -> bool:
    return shutil.which("helm") is not None


def _helm_template_monitoring() -> str:
    cmd = [
        "helm",
        "template",
        "spaceops",
        str(CHART),
        "-f",
        str(CHART / "values.yaml"),
        "-f",
        str(CHART / "values-stage.yaml"),
        "-f",
        str(CHART / "values-monitoring-stage.yaml"),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_monitoring_stage_overlay_renders_expected_components() -> None:
    docs = [doc for doc in yaml.safe_load_all(_helm_template_monitoring()) if doc]
    by_name = {
        (doc.get("kind"), doc.get("metadata", {}).get("name")): doc for doc in docs
    }
    for component in (
        "prometheus",
        "grafana",
        "postgres-exporter",
        "otel-collector",
    ):
        assert ("Service", f"spaceops-{component}") in by_name
        assert ("Deployment", f"spaceops-{component}") in by_name
        assert ("ServiceAccount", f"spaceops-{component}") in by_name


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_prometheus_scrapes_stage_targets() -> None:
    docs = [doc for doc in yaml.safe_load_all(_helm_template_monitoring()) if doc]
    config = next(
        doc
        for doc in docs
        if doc.get("kind") == "ConfigMap"
        and doc.get("metadata", {}).get("name") == "spaceops-prometheus-config"
    )
    prometheus_yml = config["data"]["prometheus.yml"]
    for expected in (
        "job_name: spaceops-api",
        "spaceops-api:8000",
        "job_name: spaceops-nats",
        "spaceops-nats:8222",
        "job_name: spaceops-postgres",
        "spaceops-postgres-exporter:9187",
        "job_name: spaceops-otel-collector",
        "spaceops-otel-collector:8888",
    ):
        assert expected in prometheus_yml


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_otel_collector_has_pr11_hardening() -> None:
    out = _helm_template_monitoring()
    assert "probabilistic_sampler:" in out
    assert "sampling_percentage: 25" in out
    assert "memory_limiter:" in out
    assert "sidecar.istio.io/inject" in out
    assert "containerPort: 13133" in out
    assert "containerPort: 8888" in out
    assert "limits:" in out


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_grafana_uses_secret_and_disables_anonymous_auth() -> None:
    out = _helm_template_monitoring()
    assert "name: spaceops-stage-monitoring-secrets" in out
    assert "key: grafana-admin-password" in out
    assert "GF_AUTH_ANONYMOUS_ENABLED" in out
    assert 'value: "false"' in out


def test_pr11_docs_and_board_mark_done() -> None:
    task = PR11.read_text(encoding="utf-8")
    board = BOARD.read_text(encoding="utf-8")
    assert "## Status\n\nDone." in task
    assert "| PR1.1 | K8s monitoring stack in Helm/GitOps | Done |" in board


def test_pr11_documentation_mentions_monitoring_overlay_and_gap() -> None:
    helm_readme = HELM_README.read_text(encoding="utf-8")
    runbook = GCP_RUNBOOK.read_text(encoding="utf-8")
    assert "values-monitoring-stage.yaml" in helm_readme
    assert "spaceops-stage-monitoring-secrets" in helm_readme
    assert (
        "Variant A agent-worker still has no standalone HTTP metrics endpoint"
        in helm_readme
    )
    assert "values-monitoring-stage.yaml" in runbook
    assert "spaceops-prometheus" in runbook
    assert "agent-worker" in runbook
    assert "api/v1/targets" in runbook
    assert "mesh-sidecar" in runbook


def test_monitoring_analysis_environment_matrix_reflects_pr11_overlay() -> None:
    analysis = (REPO_ROOT / "docs" / "monitoring-production-analysis.md").read_text(
        encoding="utf-8"
    )
    assert "GKE + PR1.1 overlay" in analysis
    assert "values-monitoring-stage.yaml" in analysis
    assert "Grafana/Prometheus no on GKE" not in analysis
