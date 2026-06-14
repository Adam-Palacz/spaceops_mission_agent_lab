"""PS6.10 — Portfolio artifacts bundle: link integrity and content tests."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO = REPO_ROOT / "docs" / "portfolio" / "README.md"
THREAT = REPO_ROOT / "docs" / "threat_model.md"
ADR_INDEX = REPO_ROOT / "docs" / "adr" / "README.md"
PS610 = (
    REPO_ROOT
    / "roadmap"
    / "02-production-scale"
    / "sprint-6"
    / "PS6.10-portfolio-artifacts-bundle.md"
)
RUNBOOKS_DIR = REPO_ROOT / "docs" / "runbooks"
DEMO_RUNBOOK = RUNBOOKS_DIR / "demo_15min.md"

# Runbooks that must appear in the portfolio runbook pack table.
REQUIRED_RUNBOOK_INDEX = [
    "demo_15min.md",
    "local_k8s_dev.md",
    "k8s_rollout_rollback.md",
    "cloud_cost_hygiene.md",
    "gcp_stage_deploy.md",
    "gcp_stage_teardown.md",
    "ci_gating_policy.md",
    "llm_cost_guardrails.md",
    "gpu_cost_hygiene.md",
    "guardrails_minimum_hardening.md",
    "distributed_tracing_ps19.md",
]

LINK_PATTERN = re.compile(r"\]\(([^)]+)\)")


def _resolve_link(source: Path, target: str) -> Path:
    raw = target.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return Path()  # external — skip
    if raw.startswith("#"):
        return Path()  # anchor only
    # Strip optional title after space and markdown anchor
    path_part = raw.split()[0].split("#")[0]
    if not path_part:
        return Path()
    if path_part.startswith("/"):
        return REPO_ROOT / path_part.lstrip("/")
    return (source.parent / path_part).resolve()


def _markdown_links(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return LINK_PATTERN.findall(text)


def test_ps610_deliverables_exist() -> None:
    assert PORTFOLIO.is_file()
    assert THREAT.is_file()
    assert ADR_INDEX.is_file()
    assert PS610.is_file()


def test_portfolio_covers_scenarios_and_paths() -> None:
    text = PORTFOLIO.read_text(encoding="utf-8")
    assert "Scenario A" in text
    assert "Scenario B" in text
    assert "portfolio-scenario-a" in text
    assert "portfolio-scenario-b" in text
    assert "make k8s-up" in text
    assert "docker compose" in text
    assert "Jaeger" in text
    assert "Dependabot" in text
    assert "External reviewer checklist" in text


def test_threat_model_maps_threats_to_controls() -> None:
    text = THREAT.read_text(encoding="utf-8")
    for threat in (
        "Prompt injection",
        "Tool abuse",
        "Data poisoning",
        "Secrets leakage",
    ):
        assert threat in text
    assert "Verification" in text
    assert "PS4" in text
    assert "PS5" in text
    assert "OPA" in text


def test_adr_index_covers_ps6_and_themes() -> None:
    text = ADR_INDEX.read_text(encoding="utf-8")
    for adr in ("0002", "0003", "0004", "0005", "0006", "0007", "0008", "0009"):
        assert adr in text
    assert "Superseded" in text
    assert "llm_gateway.md" in text


def test_portfolio_runbook_index_lists_required_runbooks() -> None:
    text = PORTFOLIO.read_text(encoding="utf-8")
    for name in REQUIRED_RUNBOOK_INDEX:
        assert name in text, name


def test_all_runbooks_on_disk_are_indexed_in_portfolio() -> None:
    on_disk = sorted(p.name for p in RUNBOOKS_DIR.glob("*.md"))
    portfolio = PORTFOLIO.read_text(encoding="utf-8")
    missing = [name for name in on_disk if name not in portfolio]
    assert not missing, f"Runbooks not in portfolio index: {missing}"


def test_portfolio_internal_links_resolve() -> None:
    broken: list[str] = []
    for link in _markdown_links(PORTFOLIO):
        resolved = _resolve_link(PORTFOLIO, link)
        if not resolved.parts:
            continue
        if not resolved.exists():
            broken.append(f"{link} -> {resolved}")
    assert not broken, broken


def test_threat_model_internal_links_resolve() -> None:
    broken: list[str] = []
    for link in _markdown_links(THREAT):
        resolved = _resolve_link(THREAT, link)
        if not resolved.parts:
            continue
        if not resolved.exists():
            broken.append(f"{link} -> {resolved}")
    assert not broken, broken


def test_demo_runbook_internal_links_resolve() -> None:
    broken: list[str] = []
    for link in _markdown_links(DEMO_RUNBOOK):
        resolved = _resolve_link(DEMO_RUNBOOK, link)
        if not resolved.parts:
            continue
        if not resolved.exists():
            broken.append(f"{link} -> {resolved}")
    assert not broken, broken


def test_adr_readme_links_resolve() -> None:
    broken: list[str] = []
    for link in _markdown_links(ADR_INDEX):
        resolved = _resolve_link(ADR_INDEX, link)
        if not resolved.parts:
            continue
        if not resolved.exists():
            broken.append(f"{link} -> {resolved}")
    assert not broken, broken


def test_infra_vs_model_cost_documented() -> None:
    text = PORTFOLIO.read_text(encoding="utf-8")
    assert "cloud_cost_hygiene.md" in text
    assert "llm_cost_guardrails.md" in text
    threat = THREAT.read_text(encoding="utf-8")
    assert "infra $" in threat.lower() or "Infra cost" in threat
