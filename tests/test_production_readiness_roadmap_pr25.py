"""Production Readiness roadmap structure and link tests."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE_DOC = REPO_ROOT / "roadmap" / "02.5-production-readiness.md"
PHASE_DIR = REPO_ROOT / "roadmap" / "02.5-production-readiness"
ROADMAP_INDEX = REPO_ROOT / "roadmap" / "README.md"
PS7_REVIEW = (
    REPO_ROOT / "roadmap" / "02-production-scale" / "sprint-7" / "SPRINT_REVIEW.md"
)
NG_README = REPO_ROOT / "roadmap" / "03-next-gen-autonomy" / "README.md"


def test_production_readiness_phase_exists() -> None:
    assert PHASE_DOC.is_file()
    assert (PHASE_DIR / "README.md").is_file()


def test_production_readiness_sprints_and_boards_exist() -> None:
    for sprint in ("sprint-1", "sprint-2", "sprint-3"):
        sprint_dir = PHASE_DIR / sprint
        assert (sprint_dir / "README.md").is_file()
        assert (sprint_dir / "BOARD.md").is_file()


def test_production_readiness_has_full_task_set() -> None:
    task_files = sorted(PHASE_DIR.glob("sprint-*/*.md"))
    task_specs = [
        path
        for path in task_files
        if path.name not in {"README.md", "BOARD.md", "SPRINT_REVIEW.md"}
    ]
    assert len(task_specs) == 12


def test_phase_links_are_indexed_and_ng_dependency_is_explicit() -> None:
    assert "02.5-production-readiness" in ROADMAP_INDEX.read_text(encoding="utf-8")
    ps7_text = PS7_REVIEW.read_text(encoding="utf-8")
    ng_text = NG_README.read_text(encoding="utf-8")
    assert "Production Readiness" in ps7_text
    assert "NG1" in ps7_text and "NG3+" in ps7_text
    assert "PR1-PR3" in ng_text
    assert "NG1-NG2 may run in parallel" in ng_text


def test_production_readiness_local_markdown_links_resolve() -> None:
    docs = [PHASE_DOC, ROADMAP_INDEX, PS7_REVIEW, NG_README]
    docs.extend(PHASE_DIR.rglob("*.md"))
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        links = re.findall(r"\[[^\]]+\]\(([^)#][^)]+)\)", text)
        for href in links:
            target = href.split("#", 1)[0]
            if "://" in target or target.startswith("mailto:"):
                continue
            assert (doc.parent / target).resolve().exists(), f"{doc}: {href}"
