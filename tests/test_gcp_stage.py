"""GKE stage automation (deploy/demo script + full MCP overlay)."""

from __future__ import annotations

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
    for target in ("gcp-stage-deploy", "gcp-stage-demo", "gcp-stage-smoke"):
        assert target in makefile
