"""PS6.6 — Helm secrets strategy (no plaintext in Git, existingSecret refs)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CHART = REPO_ROOT / "deploy" / "helm" / "spaceops"
ADR = REPO_ROOT / "docs" / "adr" / "0007-secrets-management-k8s.md"
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "k8s_secrets_bootstrap.md"
EXAMPLES = REPO_ROOT / "deploy" / "examples" / "secrets"
BOOTSTRAP_SCRIPT = REPO_ROOT / "scripts" / "k8s_secrets_bootstrap.py"

# Values files committed to Git must not contain lab password literals.
FORBIDDEN_VALUE_PATTERNS = (
    r"changeme",
    r"sk-[a-zA-Z0-9]{20,}",
    r"postgresPassword:\s*['\"]?[^'\"$\s{][^'\"]*['\"]?",  # non-empty literal
)


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


def test_openai_api_key_not_in_committed_helm_values() -> None:
    """PS6.6: secrets.openaiApiKey in values must stay empty (install-time --set only)."""
    for path in (CHART / "values.yaml", CHART / "values-dev.yaml"):
        text = path.read_text(encoding="utf-8")
        assert "sk-" not in text
        match = re.search(r"^\s*openaiApiKey:\s*(.*)$", text, re.M)
        assert match, f"openaiApiKey missing in {path.name}"
        assert match.group(1).strip() in ('""', "''", "")


def test_env_example_uses_placeholder_for_openai() -> None:
    text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=<api_key>" in text


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_stage_overlay_does_not_render_secret_stringdata() -> None:
    out = _helm_template("spaceops-stage-sec", ["values.yaml", "values-stage.yaml"])
    docs = [d for d in yaml.safe_load_all(out) if d]
    secrets = [d for d in docs if d.get("kind") == "Secret"]
    assert secrets == []
    assert "spaceops-stage-secrets" in out
    assert "secretKeyRef" in out


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_prod_overlay_does_not_render_secret_stringdata() -> None:
    out = _helm_template("spaceops-prod-sec", ["values.yaml", "values-prod.yaml"])
    docs = [d for d in yaml.safe_load_all(out) if d]
    assert not [d for d in docs if d.get("kind") == "Secret"]
    assert "spaceops-prod-secrets" in out
    assert "secretKeyRef" in out


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_dev_secret_requires_postgres_password_at_install() -> None:
    with pytest.raises(subprocess.CalledProcessError):
        _helm_template(
            "spaceops-dev-empty-pw",
            ["values.yaml", "values-dev.yaml", "values-minimal-dev.yaml"],
        )


@pytest.mark.skipif(not _helm_available(), reason="helm CLI not installed")
def test_dev_template_uses_secret_key_ref_for_openai() -> None:
    out = _helm_template(
        "spaceops-dev-sec",
        ["values.yaml", "values-dev.yaml", "values-minimal-dev.yaml"],
        ["secrets.postgresPassword=pytest-dev"],
    )
    assert "kind: Secret" in out
    assert "secretKeyRef" in out
    assert "OPENAI_API_KEY" in out
    assert "optional: true" in out


def test_committed_values_files_have_no_plaintext_passwords() -> None:
    for path in (
        CHART / "values-dev.yaml",
        CHART / "values-stage.yaml",
        CHART / "values-prod.yaml",
        CHART / "values.yaml",
    ):
        text = path.read_text(encoding="utf-8")
        assert "changeme-dev" not in text
        for pattern in FORBIDDEN_VALUE_PATTERNS:
            if pattern.startswith("postgresPassword"):
                # empty postgresPassword: "" is allowed
                if re.search(r'postgresPassword:\s*["\'][^"\']+["\']', text):
                    pytest.fail(f"Non-empty postgresPassword literal in {path}")
            elif re.search(pattern, text, re.IGNORECASE):
                pytest.fail(f"Forbidden pattern {pattern!r} in {path}")


def test_ps66_deliverables_exist() -> None:
    assert ADR.is_file()
    assert RUNBOOK.is_file()
    assert BOOTSTRAP_SCRIPT.is_file()
    assert (EXAMPLES / "README.md").is_file()
    assert (EXAMPLES / "eso" / "external-secret-stage.yaml.example").is_file()
    assert (EXAMPLES / "sops" / "spaceops-dev-secrets.sops.yaml.example").is_file()


def test_bootstrap_script_env_map_matches_adr() -> None:
    text = BOOTSTRAP_SCRIPT.read_text(encoding="utf-8")
    assert "postgres-password" in text
    assert "OPENAI_API_KEY" in text
    assert "NGC_API_KEY" in text
    adr = ADR.read_text(encoding="utf-8")
    assert "spaceops-{env}/openai-api-key" in adr


def test_makefile_has_secrets_bootstrap_target() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "k8s-secrets-bootstrap" in makefile
    assert "k8s_secrets_bootstrap.py" in makefile
