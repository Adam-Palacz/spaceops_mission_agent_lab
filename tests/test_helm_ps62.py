"""PS6.2 — Helm chart render smoke tests (no cluster)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CHART = REPO_ROOT / "deploy" / "helm" / "spaceops"

OVERLAYS: list[tuple[str, list[str], list[str]]] = [
    (
        "dev-minimal",
        ["values.yaml", "values-dev.yaml", "values-minimal-dev.yaml"],
        ["secrets.postgresPassword=pytest-dev"],
    ),
    (
        "stage",
        ["values.yaml", "values-stage.yaml"],
        [],
    ),
    (
        "prod",
        ["values.yaml", "values-prod.yaml"],
        [],
    ),
]


def _helm_available() -> bool:
    return shutil.which("helm") is not None


def _helm_template(name: str, value_files: list[str], extra_sets: list[str]) -> str:
    cmd = [
        "helm",
        "template",
        name,
        str(CHART),
    ]
    for vf in value_files:
        cmd.extend(["-f", str(CHART / vf)])
    for s in extra_sets:
        cmd.extend(["--set", s])
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
@pytest.mark.parametrize("name,value_files,extra_sets", OVERLAYS)
def test_helm_template_renders(
    name: str, value_files: list[str], extra_sets: list[str]
) -> None:
    out = _helm_template(f"spaceops-{name}", value_files, extra_sets)
    assert "kind: Deployment" in out
    docs = [d for d in yaml.safe_load_all(out) if d]
    kinds = {d.get("kind") for d in docs}
    assert "Deployment" in kinds
    assert "Service" in kinds


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_minimal_dev_includes_opa_and_api() -> None:
    out = _helm_template(
        "spaceops-min-check",
        ["values.yaml", "values-dev.yaml", "values-minimal-dev.yaml"],
        ["secrets.postgresPassword=pytest-dev"],
    )
    assert "-opa" in out
    assert "-api" in out
    assert "LLM_BACKEND" in out


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_llm_backend_from_values_not_image() -> None:
    out = _helm_template(
        "spaceops-llm",
        ["values.yaml", "values-dev.yaml", "values-minimal-dev.yaml"],
        [
            "secrets.postgresPassword=pytest-dev",
            "api.llm.backend=openai",
        ],
    )
    assert "name: LLM_BACKEND" in out
    assert 'value: "openai"' in out or "value: openai" in out


def test_chart_files_exist() -> None:
    assert (CHART / "Chart.yaml").is_file()
    assert (CHART / "values-dev.yaml").is_file()
    assert (CHART / "values-stage.yaml").is_file()
    assert (CHART / "values-prod.yaml").is_file()
    assert (CHART / "values-minimal-dev.yaml").is_file()
    assert (CHART / "templates" / "api.yaml").is_file()
