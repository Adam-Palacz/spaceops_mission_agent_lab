"""
SpaceOps Mission Agent Lab — MCP GitOps Server
Tool: create_pr(repo_path, branch, files) — write files under ops-config/, optionally push branch and create PR via GitHub API.

S2.2: Writes files locally; when GITHUB_TOKEN and GITHUB_REPO are set, creates a branch, commits, pushes, and opens a PR.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TypedDict

from mcp.server.fastmcp import FastMCP

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OPS_CONFIG_DIR = REPO_ROOT / "ops-config"


class FileSpec(TypedDict):
    path: str
    content: str


class CreatePrResult(TypedDict, total=False):
    repo_root: str
    ops_config_dir: str
    branch: str
    files: list[FileSpec]
    note: str
    pr_url: str
    push_error: str


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


def _run_git(cwd: Path, *args: str) -> tuple[bool, str]:
    """Run git command; return (success, stderr or stdout)."""
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if r.returncode != 0:
            return False, (r.stderr or r.stdout or "").strip()
        return True, (r.stdout or "").strip()
    except Exception as e:
        return False, str(e)


def _normalize_github_repo(value: str) -> str:
    """Accept 'owner/name' or 'https://github.com/owner/name' (or .git); return 'owner/name'."""
    s = (value or "").strip()
    if not s:
        return ""
    if "github.com" in s:
        # e.g. https://github.com/Adam-Palacz/spaceops_mission_agent_lab or .../repo.git
        parts = s.rstrip("/").replace(".git", "").split("github.com/")
        if len(parts) >= 2 and parts[-1]:
            return parts[-1].strip("/")
        return ""
    return s


def _push_and_create_pr(
    branch: str,
    files_rel: list[str],
    title: str,
    body: str,
) -> tuple[str | None, str | None]:
    """
    Push branch and create PR. Returns (pr_url, error_message).
    Requires config.settings.github_token and github_repo (run from repo root with PYTHONPATH=. so config loads).
    """
    try:
        from config import settings
    except ImportError:
        return None, None  # no config → local-only mode

    token = (getattr(settings, "github_token", None) or "").strip()
    repo = _normalize_github_repo(getattr(settings, "github_repo", None) or "")
    base = getattr(settings, "github_repo_base_branch", "main") or "main"
    if not token or not repo:
        return None, None

    # Ensure we're in a git repo and have no uncommitted changes in other files
    ok, out = _run_git(REPO_ROOT, "rev-parse", "--is-inside-work-tree")
    if not ok or out != "true":
        return None, "Not a git repository"

    # Create branch
    ok, err = _run_git(REPO_ROOT, "checkout", "-b", branch)
    if not ok:
        if "already exists" in err:
            _run_git(REPO_ROOT, "checkout", branch)
        else:
            return None, f"git checkout -b: {err}"

    # Add only our files (paths relative to repo root)
    for p in files_rel:
        _run_git(REPO_ROOT, "add", p)
    ok, err = _run_git(REPO_ROOT, "status", "--porcelain")
    if not ok or not err.strip():
        _run_git(REPO_ROOT, "checkout", "-")  # return to previous branch
        return None, "No changes to commit"

    # Commit
    ok, err = _run_git(REPO_ROOT, "commit", "-m", title or "GitOps: agent proposal")
    if not ok:
        _run_git(REPO_ROOT, "checkout", "-")
        return None, f"git commit: {err}"

    # Push: https://x-access-token:<token>@github.com/owner/repo.git
    push_url = f"https://x-access-token:{token}@github.com/{repo}.git"
    ok, err = _run_git(REPO_ROOT, "push", push_url, branch)
    if not ok:
        _run_git(REPO_ROOT, "checkout", "-")
        return None, f"git push: {err}"

    # Create PR via GitHub API
    import httpx

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"https://api.github.com/repos/{repo}/pulls",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json={
                    "title": title or "GitOps: agent proposal",
                    "body": body or "Agent-proposed config change.",
                    "head": branch,
                    "base": base,
                },
            )
            if resp.status_code != 201:
                return None, f"GitHub API: {resp.status_code} {resp.text[:200]}"
            data = resp.json()
            pr_url = data.get("html_url") or data.get("url") or ""
            return pr_url, None
    except Exception as e:
        return None, f"GitHub API: {e}"


mcp = FastMCP("SpaceOps GitOps", json_response=True)


def _sanitize_for_mcp(obj: dict) -> dict:
    """Ensure no None in string fields; MCP output validation rejects None for string type."""
    out: dict = {}
    for k, v in obj.items():
        if v is None:
            out[k] = ""
        elif isinstance(v, str):
            out[k] = v
        elif isinstance(v, list):
            out[k] = [_sanitize_for_mcp(x) if isinstance(x, dict) else x for x in v]
        else:
            out[k] = v
    return out


@mcp.tool()
def create_pr(
    repo_path: str | None,
    branch: str,
    files: list[FileSpec],
) -> dict:
    """
    Prepare a GitOps change by writing files under ops-config/, then optionally push and open a PR.

    Arguments:
    - repo_path: Optional filesystem path to the repo or ops-config subtree.
      When None, defaults to the local ops-config/ under the main repo root.
    - branch: Branch name for the change (e.g. \"agent/incident-123\").
      If GITHUB_TOKEN and GITHUB_REPO are set, this branch is created, pushed, and a PR is opened.
    - files: List of {\"path\", \"content\"} entries, relative to ops-config root.

    Behaviour:
    - Writes/overwrites the given files under ops-config/.
    - If GITHUB_TOKEN and GITHUB_REPO are set: creates branch, commits, pushes to origin, creates PR via GitHub API.
    - Returns a summary; pr_url or push_error are set when GitHub integration is used.
    """
    branch = (branch or "").strip() or "agent/unknown"
    ops_dir = _resolve_ops_config_dir(repo_path)
    ops_dir.mkdir(parents=True, exist_ok=True)

    normalized_files: list[FileSpec] = []
    files_rel_to_repo: list[str] = []
    for spec in files:
        rel = (spec.get("path") or "").strip() or ""
        content = spec.get("content")
        content = content if isinstance(content, str) else ""
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise ValueError(f"Invalid path for GitOps file: {rel}")
        target = ops_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        norm_path = str(rel_path).replace("\\", "/")
        normalized_files.append(FileSpec(path=norm_path, content=content))
        try:
            rel_to_repo = (ops_dir / rel_path).resolve().relative_to(REPO_ROOT)
            files_rel_to_repo.append(str(rel_to_repo).replace("\\", "/"))
        except ValueError:
            pass

    note = "Files written under ops-config/."
    result: CreatePrResult = {
        "repo_root": str(REPO_ROOT),
        "ops_config_dir": str(ops_dir),
        "branch": branch,
        "files": normalized_files,
        "note": note,
    }

    pr_url, push_error = _push_and_create_pr(
        branch=branch,
        files_rel=files_rel_to_repo,
        title=f"GitOps: {branch}",
        body="Agent-proposed config change (create_pr MCP).",
    )
    if pr_url:
        result["pr_url"] = str(pr_url)
        result["note"] = "Files written, branch pushed, PR created."
    elif push_error:
        result["push_error"] = str(push_error)
        result["note"] = "Files written; push/PR failed (see push_error)."

    return _sanitize_for_mcp(result)


if __name__ == "__main__":
    import uvicorn

    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=8004)
