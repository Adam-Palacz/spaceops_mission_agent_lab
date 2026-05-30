"""PS6.4 — rollout/rollback runbook and demo script checks (no cluster required)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "k8s_rollout_rollback.md"
DEMO_SCRIPT = REPO_ROOT / "scripts" / "k8s_rollout_demo.py"
MAKEFILE = REPO_ROOT / "Makefile"


def _load_demo_module():
    spec = importlib.util.spec_from_file_location("k8s_rollout_demo_ps64", DEMO_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_rollout_runbook_exists_and_covers_flows() -> None:
    assert RUNBOOK.is_file()
    text = RUNBOOK.read_text(encoding="utf-8")
    for snippet in (
        "helm upgrade",
        "helm rollback",
        "LLM_BACKEND=openai",
        "--atomic",
        "Incident capture template",
        "llm_backend_rollout.md",
    ):
        assert snippet in text


def test_demo_script_uses_atomic_helm_upgrade() -> None:
    mod = _load_demo_module()
    assert mod.HELM_RELEASE == "spaceops"
    assert mod.NAMESPACE == "spaceops-dev"
    source = DEMO_SCRIPT.read_text(encoding="utf-8")
    assert "--atomic" in source
    assert "api.llm.backend=openai" in source


def test_makefile_has_k8s_rollout_demo_target() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "k8s-rollout-demo:" in text


def test_llm_backend_rollout_links_k8s_runbook() -> None:
    path = REPO_ROOT / "docs" / "runbooks" / "llm_backend_rollout.md"
    text = path.read_text(encoding="utf-8")
    assert "k8s_rollout_rollback.md" in text
