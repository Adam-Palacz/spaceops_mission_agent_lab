"""PS7.4 / BL-001 — Production monitoring stack analysis document tests."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "monitoring-production-analysis.md"
PS74 = (
    REPO_ROOT
    / "roadmap"
    / "02-production-scale"
    / "sprint-7"
    / "PS7.4-monitoring-production-analysis.md"
)
BL001 = REPO_ROOT / "roadmap" / "backlog" / "BL-001-monitoring-improvement-analysis.md"
PORTFOLIO = REPO_ROOT / "docs" / "portfolio" / "README.md"
DOCS_INDEX = REPO_ROOT / "docs" / "README.md"


def test_ps74_analysis_document_exists() -> None:
    assert DOC.is_file()


def test_analysis_covers_all_components() -> None:
    text = DOC.read_text(encoding="utf-8").lower()
    for component in (
        "postgres",
        "opentelemetry collector",
        "jaeger",
        "prometheus",
        "grafana",
    ):
        assert component in text, component


def test_analysis_has_ok_gap_recommendation_structure() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "OK / Gap" in text or "OK · Gap" in text
    assert "Recommendation" in text
    assert "Production checklist" in text


def test_analysis_not_ps19_tracing_doc() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "PS1.9" in text
    assert "distributed_tracing_ps19.md" in text


def test_analysis_maps_follow_up_tasks_to_production_readiness() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "PS7b" in text
    assert "Production Readiness" in text
    for task in ("PR1.1", "PR1.2", "PR2.4"):
        assert task in text
    assert "TLS" in text or "tls" in text
    assert "sampling" in text.lower()


def test_portfolio_and_docs_index_link_analysis() -> None:
    assert "monitoring-production-analysis.md" in PORTFOLIO.read_text(encoding="utf-8")
    assert "monitoring-production-analysis.md" in DOCS_INDEX.read_text(encoding="utf-8")


def test_ps74_spec_done() -> None:
    text = PS74.read_text(encoding="utf-8")
    assert "| **Status** | Done |" in text
    assert "monitoring-production-analysis.md" in text


def test_analysis_local_markdown_links_resolve() -> None:
    text = DOC.read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)#][^)]+)\)", text)
    assert links
    for href in links:
        target = href.split("#", 1)[0]
        if "://" in target or target.startswith("mailto:"):
            continue
        assert (DOC.parent / target).resolve().exists(), href
