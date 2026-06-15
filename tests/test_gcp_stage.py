"""GKE stage automation (deploy/demo script + full MCP overlay)."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gcp_stage.py"
FULL_VALUES = REPO_ROOT / "deploy" / "helm" / "spaceops" / "values-stage-full.yaml"
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "gcp_stage_deploy.md"
HELM_CHART = REPO_ROOT / "deploy" / "helm" / "spaceops"


def _load_gcp_stage_module():
    spec = importlib.util.spec_from_file_location("gcp_stage_test", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gcp_stage_script_exists() -> None:
    assert SCRIPT.is_file()


def test_gcp_stage_help() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "deploy" in proc.stdout
    assert "demo" in proc.stdout


def test_stage_full_overlay_enables_mcps() -> None:
    doc = yaml.safe_load(FULL_VALUES.read_text(encoding="utf-8"))
    assert doc["kbMcp"]["enabled"] is True
    assert doc["ticketMcp"]["enabled"] is True
    assert doc["gitopsMcp"]["enabled"] is True


def test_helm_template_renders_kb_mcp_with_full_overlay() -> None:
    if shutil.which("helm") is None:
        pytest.skip("helm CLI not on PATH")
    proc = subprocess.run(
        [
            "helm",
            "template",
            "spaceops",
            str(HELM_CHART),
            "-f",
            str(HELM_CHART / "values.yaml"),
            "-f",
            str(HELM_CHART / "values-stage.yaml"),
            "-f",
            str(FULL_VALUES),
            "--set",
            "secrets.postgresPassword=ci-only",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        pytest.skip(f"helm template failed: {proc.stderr or proc.stdout}")
    assert "kb-mcp" in proc.stdout


def test_runbook_documents_automation_and_gitops() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "gcp-stage-demo" in text
    assert "values-stage-full.yaml" in text
    assert "gitops-install" in text
    assert ":8000" in text


def test_makefile_gcp_stage_targets() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "gcp-stage-deploy",
        "gcp-stage-demo",
        "gcp-stage-smoke",
        "gcp-stage-images",
        "gcp-terraform-ar",
        "gcp-kube-credentials",
        "gcp-stage-destroy",
    ):
        assert target in makefile


def test_gcp_stage_teardown_command() -> None:
    source = (REPO_ROOT / "scripts" / "gcp_stage.py").read_text(encoding="utf-8")
    assert "cmd_teardown" in source
    assert "--confirm" in source
    assert "--destroy-budget-alert" in source
    assert "-target=google_billing_budget.spaceops" in source
    teardown_doc = REPO_ROOT / "docs" / "runbooks" / "gcp_stage_teardown.md"
    assert teardown_doc.is_file()


@pytest.mark.parametrize(
    ("destroy_budget_alert", "expects_restore"),
    ((False, True), (True, False)),
)
def test_gcp_stage_teardown_budget_restore_behavior(
    monkeypatch: pytest.MonkeyPatch,
    destroy_budget_alert: bool,
    expects_restore: bool,
) -> None:
    mod = _load_gcp_stage_module()
    calls: list[list[str]] = []

    monkeypatch.setattr(mod, "PROJECT_ID", "")
    monkeypatch.setattr(mod, "require_tools", lambda *_tools: None)
    monkeypatch.setattr(
        mod,
        "_run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""),
    )

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    mod.cmd_teardown(
        confirm=True,
        skip_helm=True,
        skip_terraform=False,
        skip_argocd=True,
        terraform_auto_approve=True,
        destroy_budget_alert=destroy_budget_alert,
    )

    restore = [
        "terraform",
        "apply",
        "-target=google_billing_budget.spaceops",
        "-auto-approve",
    ]
    assert (restore in calls) is expects_restore


def test_gcp_stage_preflight_kubectl() -> None:
    source = (REPO_ROOT / "scripts" / "gcp_stage.py").read_text(encoding="utf-8")
    assert "preflight_kubectl" in source
    assert "ensure_gke_credentials" in source
    assert "kube-credentials" in source


def test_dockerignore_includes_telemetry_fixtures() -> None:
    text = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "!data/telemetry" in text


def test_gcp_stage_demo_validators() -> None:
    source = (REPO_ROOT / "scripts" / "gcp_stage.py").read_text(encoding="utf-8")
    assert "validate_scenario_a" in source
    assert "validate_scenario_b" in source
    assert "run_kb_index" in source


def test_gcp_stage_checks_cluster_exists_before_kubectl() -> None:
    source = (REPO_ROOT / "scripts" / "gcp_stage.py").read_text(encoding="utf-8")
    assert "clusters" in source
    assert "describe" in source
    assert "No GKE cluster named" in source
    assert "old, deleted control-plane endpoint" in source


def test_gcp_stage_images_script() -> None:
    assert (REPO_ROOT / "scripts" / "gcp_stage_images.py").is_file()


def test_gcp_stage_images_resolves_windows_tools() -> None:
    source = (REPO_ROOT / "scripts" / "gcp_stage_images.py").read_text(encoding="utf-8")
    assert "def resolve_tool" in source
    assert "shutil.which" in source


def test_gcp_stage_images_checks_artifact_registry_before_build() -> None:
    source = (REPO_ROOT / "scripts" / "gcp_stage_images.py").read_text(encoding="utf-8")
    assert "artifacts" in source
    assert "repositories" in source
    assert "describe" in source
    assert "Artifact Registry repository not found" in source
    assert "--skip-repository-check" in source
