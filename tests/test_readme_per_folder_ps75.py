"""PS7.5 / BL-002 — Folder README coverage tests."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PS75 = (
    REPO_ROOT
    / "roadmap"
    / "02-production-scale"
    / "sprint-7"
    / "PS7.5-readme-per-folder.md"
)
DOCS_INDEX = REPO_ROOT / "docs" / "README.md"

# PS7.5 hard scope — every listed folder must have README.md (BL-002 checklist).
REQUIRED_README_DIRS = [
    "data",
    "data/telemetry",
    "data/events",
    "data/ground_logs",
    "data/incidents",
    "data/approvals",
    "data/llm_runs",
    "data/eval-reports",
    "data/replay",
    "data/replay/baselines",
    "data/replay/golden",
    "data/replay/runs",
    "kb",
    "kb/runbooks",
    "kb/postmortems",
    "kb/policies",
    "evals",
    "evals/fixtures",
    "evals/fixtures/semantic",
    "infra",
    "infra/opa",
    "infra/sql",
    "infra/k8s",
    "infra/k8s/local",
    "infra/terraform",
    "infra/terraform/gcp",
    "infra/grafana",
    "infra/grafana/provisioning",
    "infra/grafana/provisioning/dashboards",
    "infra/grafana/provisioning/datasources",
    "roadmap/02-production-scale",
    "roadmap/02.5-production-readiness",
    "roadmap/03-next-gen-autonomy",
]

MIN_README_CHARS = 40


def test_ps75_spec_done() -> None:
    text = PS75.read_text(encoding="utf-8")
    assert "| **Status** | Done |" in text


def test_required_folders_have_readme() -> None:
    missing = []
    for rel in REQUIRED_README_DIRS:
        readme = REPO_ROOT / rel / "README.md"
        if not readme.is_file():
            missing.append(rel)
    assert not missing, f"Missing README.md: {missing}"


def test_readmes_are_substantive() -> None:
    thin = []
    for rel in REQUIRED_README_DIRS:
        text = (REPO_ROOT / rel / "README.md").read_text(encoding="utf-8").strip()
        if len(text) < MIN_README_CHARS:
            thin.append(rel)
    assert not thin, f"README too short (<{MIN_README_CHARS} chars): {thin}"


def test_docs_index_notes_folder_readmes() -> None:
    text = DOCS_INDEX.read_text(encoding="utf-8")
    lower = text.lower()
    assert "ps7.5" in lower or "folder readmes" in lower or "bl-002" in lower


def test_readme_local_markdown_links_resolve() -> None:
    for rel in REQUIRED_README_DIRS:
        readme = REPO_ROOT / rel / "README.md"
        text = readme.read_text(encoding="utf-8")
        links = re.findall(r"\[[^\]]+\]\(([^)#][^)]+)\)", text)
        for href in links:
            target = href.split("#", 1)[0]
            if "://" in target or target.startswith("mailto:"):
                continue
            assert (readme.parent / target).resolve().exists(), f"{readme}: {href}"
