"""PS6.7 — GitOps (Argo CD) manifest and bootstrap tests."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GITOPS = REPO_ROOT / "deploy" / "gitops"
ARGOCD = GITOPS / "argocd"
ADR = REPO_ROOT / "docs" / "adr" / "0008-gitops-argocd.md"
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "gitops_bootstrap.md"
BOOTSTRAP = REPO_ROOT / "scripts" / "gitops_bootstrap.py"
DEMO = REPO_ROOT / "scripts" / "gitops_rollout_demo.py"
GITOPS_STAGE_VALUES = (
    REPO_ROOT / "deploy" / "helm" / "spaceops" / "values-gitops-stage.yaml"
)

APPLICATION_FILES = list((ARGOCD / "applications" / "templates").glob("*.yaml"))


def _render_template_text(text: str) -> str:
    return text.replace(
        "{{ .Values.repoUrl | quote }}",
        '"https://github.com/example/spaceops_mission_agent_lab.git"',
    ).replace("{{ .Values.targetRevision | quote }}", '"main"')


def _load_bootstrap_module():
    spec = importlib.util.spec_from_file_location("gitops_bootstrap_ps67", BOOTSTRAP)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_yaml(path: Path) -> dict:
    text = _render_template_text(path.read_text(encoding="utf-8"))
    docs = [d for d in yaml.safe_load_all(text) if d]
    assert len(docs) == 1, f"expected one document in {path}"
    return docs[0]


def _apps_by_name() -> dict[str, dict]:
    return {_load_yaml(p)["metadata"]["name"]: _load_yaml(p) for p in APPLICATION_FILES}


def test_ps67_deliverables_exist() -> None:
    assert ADR.is_file()
    assert RUNBOOK.is_file()
    assert BOOTSTRAP.is_file()
    assert DEMO.is_file()
    assert (GITOPS / "README.md").is_file()
    assert (GITOPS / "flux" / "README.md").is_file()
    assert GITOPS_STAGE_VALUES.is_file()


def test_application_manifests_are_argocd_applications() -> None:
    assert len(APPLICATION_FILES) >= 2
    for path in APPLICATION_FILES:
        doc = _load_yaml(path)
        assert doc["apiVersion"] == "argoproj.io/v1alpha1"
        assert doc["kind"] == "Application"
        assert doc["spec"]["project"] == "spaceops"
        source = doc["spec"]["source"]
        assert source["path"] == "deploy/helm/spaceops"
        assert "helm" in source
        text = path.read_text(encoding="utf-8")
        assert "stringData" not in text
        assert "postgrespassword" not in text.lower().replace("_", "")


def test_stage_automated_prod_manual_sync() -> None:
    apps = _apps_by_name()
    stage = apps["spaceops-stage"]["spec"]["syncPolicy"]
    assert stage.get("automated", {}).get("selfHeal") is True
    prod = apps["spaceops-prod"]["spec"]["syncPolicy"]
    assert "automated" not in prod


def test_gitops_value_files_have_no_secrets() -> None:
    for name in ("values-gitops-stage.yaml", "values-gitops-prod.yaml"):
        text = (REPO_ROOT / "deploy" / "helm" / "spaceops" / name).read_text(
            encoding="utf-8"
        )
        assert "password" not in text.lower()
        assert "apiKey" not in text
        assert "OPENAI" not in text


def test_root_app_points_at_applications_directory() -> None:
    root = _load_yaml(ARGOCD / "root-application.yaml")
    assert root["metadata"]["name"] == "spaceops-root"
    assert root["spec"]["source"]["path"] == "deploy/gitops/argocd/applications"
    params = {
        p["name"]: p["value"] for p in root["spec"]["source"]["helm"]["parameters"]
    }
    assert params == {
        "repoUrl": "__GITOPS_REPO_URL__",
        "targetRevision": "__GITOPS_TARGET_REVISION__",
    }


def test_app_project_allows_spaceops_namespaces() -> None:
    project = _load_yaml(ARGOCD / "app-project.yaml")
    namespaces = {d["namespace"] for d in project["spec"]["destinations"]}
    assert namespaces == {"argocd", "spaceops-dev", "spaceops-stage", "spaceops-prod"}


def test_bootstrap_substitute_manifests() -> None:
    mod = _load_bootstrap_module()
    out = mod.substitute_manifests(
        "repo: __GITOPS_REPO_URL__ rev: __GITOPS_TARGET_REVISION__",
        "https://github.com/org/r.git",
        "main",
    )
    assert "https://github.com/org/r.git" in out
    assert "__GITOPS" not in out

    match = re.match(r"git@([^:]+):(.+?)(?:\.git)?$", "git@github.com:org/repo.git")
    assert match
    assert (
        f"https://{match.group(1)}/{match.group(2)}.git"
        == "https://github.com/org/repo.git"
    )


def test_makefile_gitops_targets() -> None:
    text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "gitops-install",
        "gitops-bootstrap",
        "gitops-status",
        "gitops-rollout-demo",
    ):
        assert target in text


def test_adr_defers_flux() -> None:
    text = ADR.read_text(encoding="utf-8")
    assert "Argo CD" in text
    assert "Flux" in text
    assert "deferred" in text.lower()


def test_no_real_secrets_in_gitops_tree() -> None:
    pattern = re.compile(r"sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]+")
    for path in GITOPS.rglob("*"):
        if path.suffix not in {".yaml", ".yml", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        assert not pattern.search(text), f"secret-like value in {path}"
