"""GitHub REST helpers for create_pr when local .git is unavailable (e.g. K8s image)."""

from __future__ import annotations

import base64
from typing import Iterable

import httpx

_GH_API = "2022-11-28"


def _headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": _GH_API,
    }


def create_pr_via_github_api(
    *,
    repo: str,
    token: str,
    branch: str,
    base: str,
    title: str,
    body: str,
    files: Iterable[tuple[str, str]],
) -> tuple[str | None, str | None]:
    """
    Create branch, commit file contents, open PR using GitHub API only.

    files: (repo-relative path, utf-8 content) e.g. ("ops-config/alerts/x.yaml", "...")
    """
    owner_name = repo.strip().strip("/")
    if owner_name.count("/") != 1:
        return None, f"Invalid github repo: {repo!r}"
    base_url = f"https://api.github.com/repos/{owner_name}"
    file_list = list(files)
    if not file_list:
        return None, "No files to commit"

    try:
        with httpx.Client(timeout=30.0) as client:
            ref_resp = client.get(
                f"{base_url}/git/ref/heads/{base}",
                headers=_headers(token),
            )
            if ref_resp.status_code != 200:
                return None, f"GitHub ref: {ref_resp.status_code} {ref_resp.text[:200]}"
            base_sha = ref_resp.json()["object"]["sha"]

            branch_resp = client.post(
                f"{base_url}/git/refs",
                headers=_headers(token),
                json={"ref": f"refs/heads/{branch}", "sha": base_sha},
            )
            if branch_resp.status_code not in (201, 422):
                return (
                    None,
                    f"GitHub create ref: {branch_resp.status_code} {branch_resp.text[:200]}",
                )

            for path, content in file_list:
                norm = path.replace("\\", "/").lstrip("/")
                get_resp = client.get(
                    f"{base_url}/contents/{norm}",
                    headers=_headers(token),
                    params={"ref": branch},
                )
                payload: dict = {
                    "message": title or f"GitOps: {branch}",
                    "content": base64.b64encode(content.encode("utf-8")).decode(
                        "ascii"
                    ),
                    "branch": branch,
                }
                if get_resp.status_code == 200:
                    payload["sha"] = get_resp.json().get("sha")
                put_resp = client.put(
                    f"{base_url}/contents/{norm}",
                    headers=_headers(token),
                    json=payload,
                )
                if put_resp.status_code not in (200, 201):
                    return (
                        None,
                        f"GitHub put {norm}: {put_resp.status_code} {put_resp.text[:200]}",
                    )

            pr_resp = client.post(
                f"{base_url}/pulls",
                headers=_headers(token),
                json={
                    "title": title or f"GitOps: {branch}",
                    "body": body or "Agent-proposed config change.",
                    "head": branch,
                    "base": base,
                },
            )
            if pr_resp.status_code != 201:
                return None, f"GitHub PR: {pr_resp.status_code} {pr_resp.text[:200]}"
            data = pr_resp.json()
            return data.get("html_url") or data.get("url") or "", None
    except Exception as exc:
        return None, f"GitHub API: {exc}"
