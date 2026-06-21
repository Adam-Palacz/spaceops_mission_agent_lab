"""PR1.3 — stage operating policy and readiness tests."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY = REPO_ROOT / "docs" / "runbooks" / "stage_operating_policy.md"
DEPLOY = REPO_ROOT / "docs" / "runbooks" / "gcp_stage_deploy.md"
TEARDOWN = REPO_ROOT / "docs" / "runbooks" / "gcp_stage_teardown.md"
DOCS_INDEX = REPO_ROOT / "docs" / "README.md"
BOARD = REPO_ROOT / "roadmap" / "02.5-production-readiness" / "sprint-1" / "BOARD.md"
PR13 = (
    REPO_ROOT
    / "roadmap"
    / "02.5-production-readiness"
    / "sprint-1"
    / "PR1.3-stage-operating-policy.md"
)


def test_stage_policy_selects_ephemeral_with_controls() -> None:
    text = POLICY.read_text(encoding="utf-8")
    assert "ephemeral stage by default" in text
    assert "Time-boxed long-lived stage" in text
    assert "Budget alert must stay enabled" in text
    assert "--destroy-budget-alert" in text
    assert "Full recreate target" in text
    assert "<= 75 min" in text


def test_stage_policy_documents_secrets_ownership_and_drift() -> None:
    text = POLICY.read_text(encoding="utf-8")
    for required in (
        "External Secrets Operator",
        "spaceops-stage-secrets",
        "Helm and GitOps ownership",
        "Do not let Argo CD and imperative Helm mutate the same release",
        "Drift detection drill",
        "terraform plan",
        "helm status spaceops",
        "Demo readiness checklist",
    ):
        assert required in text


def test_deploy_and_teardown_runbooks_reference_policy() -> None:
    deploy = DEPLOY.read_text(encoding="utf-8")
    teardown = TEARDOWN.read_text(encoding="utf-8")
    assert "stage_operating_policy.md" in deploy
    assert "ephemeral by default" in deploy
    assert "owner and teardown time" in deploy
    assert "stage_operating_policy.md" in teardown
    assert "Policy verification" in teardown
    assert "terraform state list" in teardown


def test_pr13_docs_board_and_index_are_updated() -> None:
    assert (
        "| PR1.3 | Long-lived stage policy and readiness | Done |"
        in BOARD.read_text(encoding="utf-8")
    )
    pr_text = PR13.read_text(encoding="utf-8")
    assert "## Status\n\nDone." in pr_text
    assert "ephemeral stage by default" in pr_text
    assert "stage_operating_policy.md" in DOCS_INDEX.read_text(encoding="utf-8")


def test_stage_policy_local_markdown_links_resolve() -> None:
    for doc in (POLICY, DEPLOY, TEARDOWN, PR13):
        text = doc.read_text(encoding="utf-8")
        links = re.findall(r"\[[^\]]+\]\(([^)#][^)]+)\)", text)
        for href in links:
            target = href.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            assert (doc.parent / target).resolve().exists(), f"{doc}: {href}"
