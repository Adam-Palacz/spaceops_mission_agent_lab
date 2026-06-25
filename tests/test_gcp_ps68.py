"""PS6.8 — GCP baseline Terraform skeleton and runbook tests."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
TF_DIR = REPO_ROOT / "infra" / "terraform" / "gcp"
ADR = REPO_ROOT / "docs" / "adr" / "0009-gcp-baseline-portable-first.md"
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "gcp_stage_deploy.md"
GCP_VALUES = REPO_ROOT / "deploy" / "helm" / "spaceops" / "values-gcp-stage.yaml"
PS69 = (
    REPO_ROOT
    / "roadmap"
    / "02-production-scale"
    / "sprint-6"
    / "PS6.9-billing-shutdown-controls.md"
)

REQUIRED_TF = [
    "versions.tf",
    "variables.tf",
    "main.tf",
    "outputs.tf",
    "terraform.tfvars.example",
    "terraform.pr14-stable.tfvars.example",
    "README.md",
]


def test_ps68_deliverables_exist() -> None:
    assert ADR.is_file()
    assert RUNBOOK.is_file()
    assert GCP_VALUES.is_file()
    assert (TF_DIR / ".gitignore").is_file()
    for name in REQUIRED_TF:
        assert (TF_DIR / name).is_file(), name


def test_terraform_declares_core_resources() -> None:
    main = (TF_DIR / "main.tf").read_text(encoding="utf-8")
    for snippet in (
        "google_container_cluster",
        "google_artifact_registry_repository",
        "google_service_account",
        "google_service_account.eso",
        "compute.googleapis.com",
        "node_locations",
        "node_config",
        "node_disk_type",
        "depends_on = [google_project_service.apis]",
    ):
        assert snippet in main


def test_readme_covers_vars_state_cost_destroy() -> None:
    readme = (TF_DIR / "README.md").read_text(encoding="utf-8").lower()
    for topic in ("variable", "state", "cost", "terraform destroy", "portability"):
        assert topic in readme, topic
    assert "pr1.4 stable stage profile" in readme


def test_pr14_stable_tfvars_uses_non_preemptible_capacity() -> None:
    text = (TF_DIR / "terraform.pr14-stable.tfvars.example").read_text(encoding="utf-8")
    assert "node_count        = 2" in text
    assert 'machine_type      = "e2-standard-4"' in text
    assert "preemptible_nodes = false" in text


def test_runbook_portability_and_ps69_crosslink() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "values-stage.yaml" in text
    assert "values-gcp-stage.yaml" in text
    assert "Cloud Run" in text
    assert "PS6.9" in text or PS69.name in text


def test_gcp_values_overlay_loadbalancer_and_registry() -> None:
    doc = yaml.safe_load(GCP_VALUES.read_text(encoding="utf-8"))
    assert doc["api"]["service"]["type"] == "LoadBalancer"
    assert "docker.pkg.dev" in doc["images"]["api"]["repository"]


def test_adr_portable_first_no_gke_lockin() -> None:
    adr = ADR.read_text(encoding="utf-8")
    assert "portable" in adr.lower()
    assert "Cloud Run" in adr
    assert "No GKE" in adr or "no GKE" in adr.lower()


def test_makefile_has_terraform_gcp_validate_target() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "terraform-gcp-validate" in makefile


def test_ci_workflows_exist() -> None:
    assert (
        REPO_ROOT / ".github" / "workflows" / "gcp-terraform-validate.yml"
    ).is_file()
    assert (
        REPO_ROOT / ".github" / "workflows" / "gcp-artifact-registry-push.yml"
    ).is_file()
    push_wf = (
        REPO_ROOT / ".github" / "workflows" / "gcp-artifact-registry-push.yml"
    ).read_text(encoding="utf-8")
    assert "workflow_dispatch" in push_wf


def test_terraform_validate_when_cli_available() -> None:
    if shutil.which("terraform") is None:
        return
    init = subprocess.run(
        ["terraform", "init", "-backend=false"],
        cwd=TF_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    assert init.returncode == 0, init.stderr
    validate = subprocess.run(
        ["terraform", "validate"],
        cwd=TF_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    assert validate.returncode == 0, validate.stderr


def test_no_app_gke_imports() -> None:
    apps = REPO_ROOT / "apps"
    if not apps.is_dir():
        return
    gke_pattern = re.compile(r"google\.cloud|kubernetes\.client|gke_", re.I)
    for py in apps.rglob("*.py"):
        content = py.read_text(encoding="utf-8", errors="ignore")
        assert not gke_pattern.search(content), f"GKE coupling in {py}"
