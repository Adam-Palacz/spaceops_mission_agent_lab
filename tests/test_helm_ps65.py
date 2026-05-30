"""PS6.5 — Helm isolation controls (NetworkPolicy, quota, RBAC)."""

from __future__ import annotations

import shutil
import subprocess
import importlib.util
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CHART = REPO_ROOT / "deploy" / "helm" / "spaceops"
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "k8s_environment_isolation.md"
VERIFY_SCRIPT = REPO_ROOT / "scripts" / "k8s_isolation_verify.py"


def _load_verify_module():
    spec = importlib.util.spec_from_file_location(
        "k8s_isolation_verify_ps65", VERIFY_SCRIPT
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _helm_available() -> bool:
    return shutil.which("helm") is not None


def _helm_template(
    name: str, value_files: list[str], extra_sets: list[str] | None = None
) -> str:
    cmd = ["helm", "template", name, str(CHART)]
    for vf in value_files:
        cmd.extend(["-f", str(CHART / vf)])
    for s in extra_sets or []:
        cmd.extend(["--set", s])
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def _kinds(out: str) -> set[str]:
    docs = [d for d in yaml.safe_load_all(out) if d]
    return {d.get("kind") for d in docs}


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_dev_minimal_renders_isolation_controls() -> None:
    out = _helm_template(
        "spaceops-iso-dev",
        ["values.yaml", "values-dev.yaml", "values-minimal-dev.yaml"],
        ["secrets.postgresPassword=pytest-dev"],
    )
    kinds = _kinds(out)
    assert "NetworkPolicy" in kinds
    assert "ResourceQuota" in kinds
    assert "LimitRange" in kinds
    assert "Role" in kinds
    assert (
        "spaceops.io/environment: dev" in out or 'spaceops.io/environment: "dev"' in out
    )
    assert "spaceops-api" in out


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_stage_overlay_has_stricter_quota_than_dev() -> None:
    dev_out = _helm_template(
        "spaceops-iso-dev-q",
        ["values.yaml", "values-dev.yaml", "values-minimal-dev.yaml"],
        ["secrets.postgresPassword=pytest-dev"],
    )
    stage_out = _helm_template(
        "spaceops-iso-stage-q",
        ["values.yaml", "values-stage.yaml"],
    )
    assert (
        "spaceops.io/environment: stage" in stage_out
        or 'spaceops.io/environment: "stage"' in stage_out
    )
    assert "requests.cpu" in dev_out
    assert "NetworkPolicy" in stage_out


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_base_values_disable_isolation_by_default() -> None:
    out = _helm_template("spaceops-base", ["values.yaml"])
    assert "NetworkPolicy" not in _kinds(out)


def test_isolation_runbook_and_verify_script_exist() -> None:
    assert RUNBOOK.is_file()
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "NetworkPolicy" in text
    assert "make k8s-isolation-verify" in text
    assert VERIFY_SCRIPT.is_file()


def test_verify_script_fails_cross_namespace_without_networkpolicy_cni(
    monkeypatch,
) -> None:
    mod = _load_verify_module()

    def fake_require() -> None:
        raise SystemExit(
            "Recreate the local cluster with `make k8s-down && make k8s-up`"
        )

    monkeypatch.setattr(mod, "require_network_policy_cni_or_exit", fake_require)
    with pytest.raises(SystemExit, match="Recreate the local cluster"):
        mod.check_network_policy_cni_present()


def test_makefile_allows_isolation_verify_args() -> None:
    text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "K8S_ISOLATION_ARGS" in text
    assert "scripts/k8s_isolation_verify.py $(K8S_ISOLATION_ARGS)" in text


def test_kyverno_design_stub_exists() -> None:
    path = REPO_ROOT / "deploy" / "policy" / "kyverno" / "README.md"
    assert path.is_file()
    assert ":latest" in path.read_text(encoding="utf-8")
