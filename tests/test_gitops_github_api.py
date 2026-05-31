"""Tests for GitHub API create_pr path (K8s / no local .git)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from apps.mcp.gitops_server.github_api import create_pr_via_github_api


def test_create_pr_via_github_api_success() -> None:
    responses = [
        MagicMock(status_code=200, json=lambda: {"object": {"sha": "abc123"}}),
        MagicMock(status_code=201),
        MagicMock(status_code=404),
        MagicMock(status_code=201),
        MagicMock(
            status_code=201,
            json=lambda: {"html_url": "https://github.com/o/r/pull/1"},
        ),
    ]

    mock_client = MagicMock()
    mock_client.get.side_effect = [responses[0], responses[2]]
    mock_client.post.side_effect = [responses[1], responses[4]]
    mock_client.put.return_value = responses[3]
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch(
        "apps.mcp.gitops_server.github_api.httpx.Client", return_value=mock_client
    ):
        url, err = create_pr_via_github_api(
            repo="o/r",
            token="tok",
            branch="agent/demo",
            base="main",
            title="GitOps test",
            body="body",
            files=[("ops-config/alerts/x.yaml", "threshold: 1\n")],
        )

    assert err is None
    assert url == "https://github.com/o/r/pull/1"
