"""PS6.11 — Checkpoint ops: Helm env, runbook, retention stub, demo script."""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CHART = REPO_ROOT / "deploy" / "helm" / "spaceops"
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "graph_worker_checkpoint_ops.md"
REPLAY = REPO_ROOT / "docs" / "runbooks" / "replay_workflow.md"
ROLLOUT = REPO_ROOT / "docs" / "runbooks" / "k8s_rollout_rollback.md"
DEMO = REPO_ROOT / "scripts" / "k8s_checkpoint_demo.py"
RETENTION = REPO_ROOT / "scripts" / "checkpoint_retention.py"
CHECKPOINT_VALUES = CHART / "values-checkpoint-dev.yaml"


def _helm_available() -> bool:
    return shutil.which("helm") is not None


def _helm_template(value_files: list[str], extra_sets: list[str] | None = None) -> str:
    cmd = ["helm", "template", "spaceops-ckpt", str(CHART)]
    for vf in value_files:
        cmd.extend(["-f", str(CHART / vf)])
    for s in extra_sets or []:
        cmd.extend(["--set", s])
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return proc.stdout


def _api_env_block(rendered: str) -> str:
    m = re.search(
        r"name: AGENT_DURABLE_CHECKPOINT_ENABLED\n\s+value: (.+)",
        rendered,
    )
    assert m, "AGENT_DURABLE_CHECKPOINT_ENABLED not found in render"
    return m.group(1).strip().strip('"').strip("'")


def test_ps611_deliverables_exist() -> None:
    assert RUNBOOK.is_file()
    assert DEMO.is_file()
    assert RETENTION.is_file()
    assert CHECKPOINT_VALUES.is_file()


def test_runbook_variant_b_and_kubectl_commands() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "Variant B" in text
    assert "POST /runs/resume" in text
    assert "kubectl delete pod" in text
    assert "agent_graph_checkpoints" in text
    assert "Variant A" in text
    assert "HPA" in text
    assert "retention" in text.lower()
    assert "replay_workflow.md" in text


def test_rollout_and_replay_cross_links() -> None:
    assert "graph_worker_checkpoint_ops.md" in ROLLOUT.read_text(encoding="utf-8")
    assert "graph_worker_checkpoint_ops.md" in REPLAY.read_text(encoding="utf-8")


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_stage_enables_checkpoint_on_api() -> None:
    out = _helm_template(["values.yaml", "values-stage.yaml"])
    assert _api_env_block(out) == "true"
    docs = [d for d in yaml.safe_load_all(out) if d and d.get("kind") == "Deployment"]
    api_deps = [
        d for d in docs if d.get("metadata", {}).get("name", "").endswith("-api")
    ]
    assert api_deps, "api Deployment missing"
    worker_deps = [
        d for d in docs if "agent-worker" in d.get("metadata", {}).get("name", "")
    ]
    assert not worker_deps


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_minimal_dev_checkpoint_disabled_by_default() -> None:
    out = _helm_template(
        ["values.yaml", "values-dev.yaml", "values-minimal-dev.yaml"],
        ["secrets.postgresPassword=test"],
    )
    assert _api_env_block(out) == "false"


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_checkpoint_dev_overlay_enables_flag() -> None:
    out = _helm_template(
        [
            "values.yaml",
            "values-dev.yaml",
            "values-minimal-dev.yaml",
            "values-checkpoint-dev.yaml",
        ],
        ["secrets.postgresPassword=test"],
    )
    assert _api_env_block(out) == "true"


def test_checkpoint_dev_values_structure() -> None:
    doc = yaml.safe_load(CHECKPOINT_VALUES.read_text(encoding="utf-8"))
    assert doc["api"]["checkpoint"]["enabled"] is True


def test_k8s_checkpoint_demo_dry_run_variant_a() -> None:
    proc = subprocess.run(
        [sys.executable, str(DEMO), "--dry-run", "--variant-a"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "values-checkpoint-variant-a.yaml" in proc.stdout
    assert "agent-worker" in proc.stdout


def test_k8s_checkpoint_demo_dry_run() -> None:
    # Dry-run path only — do not import main with side effects; subprocess instead
    proc = subprocess.run(
        [__import__("sys").executable, str(DEMO), "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "POST /runs/resume" in proc.stdout
    assert "values-checkpoint-dev.yaml" in proc.stdout


def test_retention_script_parse_args(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    spec = importlib.util.spec_from_file_location(
        "checkpoint_retention_ps611", RETENTION
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(
        sys,
        "argv",
        ["checkpoint_retention.py", "--dry-run", "--older-than-days", "7"],
    )
    args = mod._parse_args()
    assert args.dry_run is True
    assert args.older_than_days == 7
    assert args.apply is False
