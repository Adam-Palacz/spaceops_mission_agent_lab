"""PS6.5 — Calico / CNI helpers for local kind."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CNI_SCRIPT = REPO_ROOT / "scripts" / "k8s_cluster_cni.py"


def _load_cni_module():
    spec = importlib.util.spec_from_file_location("k8s_cluster_cni_ps65", CNI_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_kind_config_disables_default_cni() -> None:
    import yaml

    data = yaml.safe_load(
        (REPO_ROOT / "infra" / "k8s" / "local" / "kind-config.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert data["networking"]["disableDefaultCNI"] is True


def test_network_policy_cni_detects_calico(monkeypatch) -> None:
    mod = _load_cni_module()
    monkeypatch.setattr(mod, "list_pod_names", lambda: "kube-system/calico-node-abc\n")
    assert mod.network_policy_cni_present() is True


def test_kindnet_without_policy_cni(monkeypatch) -> None:
    mod = _load_cni_module()
    monkeypatch.setattr(mod, "list_pod_names", lambda: "kube-system/kindnet-abc\n")
    assert mod.kindnet_without_policy_cni() is True


def test_require_network_policy_cni_exits_without_capable_cni(monkeypatch) -> None:
    mod = _load_cni_module()
    monkeypatch.setattr(mod, "list_pod_names", lambda: "kube-system/kindnet-abc\n")
    with pytest.raises(SystemExit, match="Recreate the local cluster"):
        mod.require_network_policy_cni_or_exit()


def test_makefile_supports_skip_calico() -> None:
    text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "K8S_SKIP_CALICO" in text
    assert "--skip-calico" in text
