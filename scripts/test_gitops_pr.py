"""
Test GitOps MCP create_pr: local write only, or push + open PR when GITHUB_TOKEN/GITHUB_REPO set.

Run from repo root. Start the GitOps server first (terminal 1), then run this script (terminal 2).

  Terminal 1:
    python -m apps.mcp.gitops_server.main

  Terminal 2:
    python scripts/test_gitops_pr.py

When push/PR is enabled, create_pr can take 30+ seconds (git push + GitHub API). If the script
returns None, the server may still have created the PR; check the repo. Run with --verbose to see
the actual error (e.g. connection refused, timeout).
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on path
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))


def _branch_name() -> str:
    """Unikalna nazwa brancha: agent/test-YYYYMMDD-HHMMSS."""
    now = datetime.now(timezone.utc)
    return now.strftime("agent/test-%Y%m%d-%H%M%S")


def _check_server_reachable(url: str) -> bool:
    """Sprawdza, czy serwer GitOps odpowiada (port otwarty)."""
    try:
        import urllib.parse

        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8004
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def main() -> None:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    branch = _branch_name()
    # Unikalna treść przy każdym uruchomieniu, żeby git widział zmianę (inaczej "No changes to commit")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    files = [
        {
            "path": "alerts/test_threshold.yaml",
            "content": f"# Test from scripts/test_gitops_pr.py\n# branch: {branch}\n# at: {ts}\nthreshold: 0.9\n",
        },
    ]
    # Sprawdź, czy serwer jest uruchomiony
    from config import settings

    url = getattr(settings, "gitops_mcp_url", "http://localhost:8004/mcp")
    if not _check_server_reachable(url):
        print("GitOps server nie odpowiada na", url)
        print("Uruchom serwer w osobnym terminalu (z katalogu głównego repo):")
        print("  python -m apps.mcp.gitops_server.main")
        sys.exit(1)
    print("Calling create_pr (may take 30+ s if push/PR enabled):", branch)
    if verbose:
        _run_with_verbose(branch, files)
    else:
        _run_normal(branch, files)


def _run_normal(branch: str, files: list[dict]) -> None:
    from apps.agent.mcp_client import call_create_pr

    result = call_create_pr(repo_path=None, branch=branch, files=files)
    _print_result(result, suggest_verbose=True)


def _run_with_verbose(branch: str, files: list[dict]) -> None:
    """Call MCP without swallowing exceptions; on decode failure print raw response."""
    from config import settings
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    from apps.agent.mcp_client import _decode_single_result

    url = getattr(settings, "gitops_mcp_url", "http://localhost:8004/mcp")

    async def _call() -> tuple[dict | None, object]:
        async with streamable_http_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                raw = await session.call_tool(
                    "create_pr",
                    arguments={"repo_path": None, "branch": branch, "files": files},
                )
                decoded = _decode_single_result(raw)
                return decoded, raw

    try:
        result, raw = asyncio.run(_call())
        if result is None:
            print(
                "Odpowiedź serwera nie została rozpoznana (decode zwrócił None). Raw:"
            )
            print("  type:", type(raw))
            if raw is not None:
                for attr in (
                    "content",
                    "structured_content",
                    "structuredContent",
                    "data",
                    "is_error",
                    "isError",
                ):
                    if hasattr(raw, attr):
                        print(f"  {attr}:", getattr(raw, attr))
            sys.exit(1)
        _print_result(result, suggest_verbose=False)
    except Exception as e:
        print(f"Error: {e}")
        print(
            "(Server may still have created the PR if it received the request; check the repo.)"
        )
        sys.exit(1)


def _print_result(result: dict | None, *, suggest_verbose: bool) -> None:
    if result is None:
        print("create_pr returned None.")
        print(
            "  - Is the GitOps server running on port 8004? (python -m apps.mcp.gitops_server.main)"
        )
        if suggest_verbose:
            print(
                "  - Run with --verbose to see the actual error (e.g. connection refused, timeout)."
            )
        sys.exit(1)
    print("Result:")
    for k, v in result.items():
        if k == "files":
            print(f"  {k}: [{len(v)} file(s)]")
        else:
            print(f"  {k}: {v}")
    if result.get("pr_url"):
        print("\nPR created:", result["pr_url"])
    elif result.get("push_error"):
        print("\nPush/PR error:", result["push_error"])


if __name__ == "__main__":
    main()
