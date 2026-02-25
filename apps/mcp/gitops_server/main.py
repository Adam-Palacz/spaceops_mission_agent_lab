"""
SpaceOps Mission Agent Lab — MCP GitOps Server
Tool: create_pr(repo_path, branch, files) — prepare config changes under ops-config/.

S2.2: For now, this server writes the requested files into the target repo working
tree (typically the ops-config/ subtree of the main repo) and returns a summary
of the changes. Git branch/PR creation is intended to be wired via git/GitHub
in a later iteration; this implementation focuses on deterministic, local changes
that are easy to review and test.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from mcp.server.fastmcp import FastMCP


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OPS_CONFIG_DIR = REPO_ROOT / "ops-config"


class FileSpec(TypedDict):
    path: str
    content: str


class CreatePrResult(TypedDict):
    repo_root: str
    ops_config_dir: str
    branch: str
    files: list[FileSpec]
    note: str


def _resolve_ops_config_dir(repo_path: str | None) -> Path:
    """
    Resolve the ops-config directory for GitOps operations.

    - If repo_path is provided, treat it as a path to the repo root or to
      the ops-config directory itself.
    - Otherwise, default to REPO_ROOT / \"ops-config\".
    """
    if repo_path:
        p = Path(repo_path)
        if (p / "alerts").exists() or (p / "channels").exists():
            return p.resolve()
        if (p / "ops-config").exists():
            return (p / "ops-config").resolve()
        return p.resolve()
    return DEFAULT_OPS_CONFIG_DIR.resolve()


mcp = FastMCP("SpaceOps GitOps", json_response=True)


@mcp.tool()
def create_pr(
    repo_path: str | None,
    branch: str,
    files: list[FileSpec],
) -> CreatePrResult:
    """
    Prepare a GitOps change by writing files under ops-config/.

    Arguments:
    - repo_path: Optional filesystem path to the repo or ops-config subtree.
      When None, defaults to the local ops-config/ under the main repo root.
    - branch: Logical branch name for the change (e.g. \"agent/incident-123\").
      Currently used for metadata only; actual git branching/PR is left to CI/operator.
    - files: List of {\"path\", \"content\"} entries, relative to ops-config root.

    Behaviour (MVP):
    - Ensures ops-config/ exists.
    - Writes/overwrites the given files under ops-config/.
    - Returns a summary of the operation that Act/approval layers can log or surface.
    """
    ops_dir = _resolve_ops_config_dir(repo_path)
    ops_dir.mkdir(parents=True, exist_ok=True)

    normalized_files: list[FileSpec] = []
    for spec in files:
        rel = spec.get("path") or ""
        content = spec.get("content") or ""
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            # For safety, restrict to paths under ops-config.
            raise ValueError(f"Invalid path for GitOps file: {rel}")
        target = ops_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        normalized_files.append(
            FileSpec(path=str(rel_path).replace("\\", "/"), content=content)
        )

    note = (
        "Files written under ops-config/; git branch/push/PR are expected to be handled "
        "by the surrounding CI or future GitHub integration."
    )
    return CreatePrResult(
        repo_root=str(REPO_ROOT),
        ops_config_dir=str(ops_dir),
        branch=branch,
        files=normalized_files,
        note=note,
    )


if __name__ == "__main__":
    import uvicorn

    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=8004)
