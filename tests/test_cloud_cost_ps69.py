"""PS6.9 — Cloud cost hygiene runbook, scripts, and Terraform budget tests."""

from __future__ import annotations

import importlib.util
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "cloud_cost_hygiene.md"
GPU_RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "gpu_cost_hygiene.md"
LLM_RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "llm_cost_guardrails.md"
TF_DIR = REPO_ROOT / "infra" / "terraform" / "gcp"
SCALE_DOWN = REPO_ROOT / "scripts" / "cloud" / "schedule_scale_down.py"
SCALE_DOWN_SH = REPO_ROOT / "scripts" / "cloud" / "schedule_scale_down.sh"
BUDGET_SH = REPO_ROOT / "scripts" / "cloud" / "gcp_budget_setup.sh"
ORPHAN_SH = REPO_ROOT / "scripts" / "cloud" / "gcp_orphan_review.sh"
PS69 = (
    REPO_ROOT
    / "roadmap"
    / "02-production-scale"
    / "sprint-6"
    / "PS6.9-billing-shutdown-controls.md"
)


def _load_scale_down_module():
    spec = importlib.util.spec_from_file_location(
        "schedule_scale_down_ps69", SCALE_DOWN
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ps69_deliverables_exist() -> None:
    assert RUNBOOK.is_file()
    assert (TF_DIR / "budget.tf").is_file()
    assert SCALE_DOWN.is_file()
    assert SCALE_DOWN_SH.is_file()
    assert BUDGET_SH.is_file()
    assert ORPHAN_SH.is_file()
    assert (REPO_ROOT / "scripts" / "cloud" / "README.md").is_file()


def test_runbook_covers_minimum_topics() -> None:
    text = RUNBOOK.read_text(encoding="utf-8").lower()
    for topic in (
        "infra $",
        "model $",
        "budget",
        "scale-down",
        "orphan",
        "gpu",
        "env",
        "llm",
    ):
        assert topic in text, topic


def test_runbook_cross_links_gpu_and_llm() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "gpu_cost_hygiene.md" in text
    assert "llm_cost_guardrails.md" in text
    assert "gcp_stage_deploy.md" in text


def test_gpu_runbook_links_cloud_doc() -> None:
    text = GPU_RUNBOOK.read_text(encoding="utf-8")
    assert "cloud_cost_hygiene.md" in text


def test_terraform_budget_optional_by_default() -> None:
    vars_tf = (TF_DIR / "variables.tf").read_text(encoding="utf-8")
    assert "enable_budget_alert" in vars_tf
    assert "default     = false" in vars_tf
    budget = (TF_DIR / "budget.tf").read_text(encoding="utf-8")
    assert "google_billing_budget" in budget
    assert "billing_account_id" in budget
    assert 'replace(var.billing_account_id, "billingAccounts/", "")' in budget
    assert "data.google_project.current.number" in budget
    assert "var.budget_currency_code" in budget


def test_schedule_scale_down_builds_gcloud_command() -> None:
    mod = _load_scale_down_module()
    args = argparse.Namespace(
        project="demo-proj",
        region="us-central1",
        cluster="spaceops-stage",
        node_pool="spaceops-stage-pool",
        nodes=0,
        dry_run=True,
    )
    cmd = mod.build_gcloud_command(args)
    assert cmd[0] == "gcloud"
    assert "resize" in cmd
    assert "--num-nodes" in cmd
    assert cmd[cmd.index("--num-nodes") + 1] == "0"


def test_makefile_has_cloud_scale_down_check() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "cloud-scale-down-check" in makefile


def test_terraform_validate_includes_budget_tf() -> None:
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


def test_scale_down_dry_run_subprocess() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(SCALE_DOWN),
            "--dry-run",
            "--project",
            "demo-proj",
            "--nodes",
            "0",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "would_run=" in proc.stdout
    assert "num-nodes" in proc.stdout or "--num-nodes" in proc.stdout
