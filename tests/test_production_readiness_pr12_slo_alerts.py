"""PR1.2 — SLO dashboard and alert rules tests."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CHART = REPO_ROOT / "deploy" / "helm" / "spaceops"
SLO_DOC = REPO_ROOT / "docs" / "slo-production-readiness.md"
PR12 = (
    REPO_ROOT
    / "roadmap"
    / "02.5-production-readiness"
    / "sprint-1"
    / "PR1.2-slo-alerts.md"
)
BOARD = REPO_ROOT / "roadmap" / "02.5-production-readiness" / "sprint-1" / "BOARD.md"
GCP_RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "gcp_stage_deploy.md"
DOCS_INDEX = REPO_ROOT / "docs" / "README.md"


def _helm_available() -> bool:
    return shutil.which("helm") is not None


def _helm_template_monitoring() -> list[dict]:
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
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def _configmap(docs: list[dict], name: str) -> dict:
    return next(
        doc
        for doc in docs
        if doc.get("kind") == "ConfigMap"
        and doc.get("metadata", {}).get("name") == name
    )


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_prometheus_loads_slo_rule_file() -> None:
    config = _configmap(_helm_template_monitoring(), "spaceops-prometheus-config")
    prometheus_yml = yaml.safe_load(config["data"]["prometheus.yml"])
    assert prometheus_yml["rule_files"] == ["/etc/prometheus/rules/*.yml"]


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_slo_alert_rules_render_with_routes_and_severities() -> None:
    rules_cm = _configmap(_helm_template_monitoring(), "spaceops-prometheus-rules")
    rules = yaml.safe_load(rules_cm["data"]["spaceops-slo-rules.yml"])
    rendered = {
        rule["alert"]: rule
        for group in rules["groups"]
        for rule in group["rules"]
        if "alert" in rule
    }
    for alert in (
        "SpaceOpsApiDown",
        "SpaceOpsSlowRunP95",
        "SpaceOpsHighRunErrorRate",
        "SpaceOpsHighEscalationRate",
        "SpaceOpsEvidencePolicyViolations",
        "SpaceOpsOpaToolFailures",
        "SpaceOpsLlmBudgetExceeded",
        "SpaceOpsNatsScrapeDown",
        "SpaceOpsPostgresExporterDown",
        "SpaceOpsSyntheticPr12Probe",
    ):
        assert alert in rendered
        assert rendered[alert]["labels"]["severity"] in {"page", "ticket"}
        assert rendered[alert]["labels"]["route"]
        assert "runbook" in rendered[alert]["annotations"]
    assert rendered["SpaceOpsSyntheticPr12Probe"]["expr"] == "vector(0)"


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_grafana_dashboard_contains_slo_panels() -> None:
    grafana = _configmap(_helm_template_monitoring(), "spaceops-grafana-provisioning")
    dashboard = json.loads(grafana["data"]["spaceops-overview.json"])
    titles = {panel["title"] for panel in dashboard["panels"]}
    for title in (
        "API availability",
        "Run error rate",
        "Escalation rate",
        "Evidence violations",
        "OPA failures",
        "Budget exceeded escalations",
        "API p95 run latency",
    ):
        assert title in titles


def test_pr12_docs_board_and_runbook_are_updated() -> None:
    assert SLO_DOC.is_file()
    assert "SpaceOpsSyntheticPr12Probe" in SLO_DOC.read_text(encoding="utf-8")
    assert "| PR1.2 | SLO dashboards and alert rules | Done |" in BOARD.read_text(
        encoding="utf-8"
    )
    assert "## Status\n\nDone." in PR12.read_text(encoding="utf-8")
    runbook = GCP_RUNBOOK.read_text(encoding="utf-8")
    assert "api/v1/rules" in runbook
    assert "api/v1/alerts" in runbook
    assert "SpaceOpsSyntheticPr12Probe" in runbook
    assert "slo-production-readiness.md" in DOCS_INDEX.read_text(encoding="utf-8")
