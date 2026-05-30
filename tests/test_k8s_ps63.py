"""PS6.3 — local K8s bootstrap tests (no cluster required for unit checks)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
KIND_CONFIG = REPO_ROOT / "infra" / "k8s" / "local" / "kind-config.yaml"
K8S_SCRIPT = REPO_ROOT / "scripts" / "k8s_local.py"
MAKEFILE = REPO_ROOT / "Makefile"


def _load_k8s_module():
    spec = importlib.util.spec_from_file_location("k8s_local_ps63", K8S_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_kind_config_exists_and_valid() -> None:
    assert KIND_CONFIG.is_file()
    data = yaml.safe_load(KIND_CONFIG.read_text(encoding="utf-8"))
    assert data["kind"] == "Cluster"
    assert data["name"] == "spaceops-dev"


def test_helm_value_files_list_complete() -> None:
    mod = _load_k8s_module()
    names = [Path(p).name for p in mod.helm_value_files()]
    assert names == ["values.yaml", "values-dev.yaml", "values-minimal-dev.yaml"]


def test_compose_cmd_uses_repo_root() -> None:
    mod = _load_k8s_module()
    cmd = mod.compose_cmd("build", "api")
    assert str(REPO_ROOT) in cmd
    assert any("docker-compose.yml" in part for part in cmd)


def test_makefile_has_k8s_targets() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    for target in ("k8s-up", "k8s-down", "k8s-status", "k8s-smoke"):
        assert f"{target}:" in text


def test_local_k8s_runbook_exists() -> None:
    path = REPO_ROOT / "docs" / "runbooks" / "local_k8s_dev.md"
    assert path.is_file()
    content = path.read_text(encoding="utf-8")
    assert "make k8s-up" in content
    assert "kind" in content.lower()


def test_compose_built_image_ref_uses_project_name() -> None:
    mod = _load_k8s_module()
    ref = mod.compose_built_image_ref("telemetry-mcp")
    assert ref.endswith("-telemetry-mcp:latest")
    assert ref.startswith("spaceops")
