from __future__ import annotations

import os
import socket
import subprocess
import sys
from urllib.parse import urlparse

import pytest


def _db_url() -> str:
    return (
        os.getenv("ALEMBIC_DATABASE_URL", "").strip()
        or os.getenv("DATABASE_URL", "").strip()
    )


def _postgres_reachable(url: str, *, timeout_seconds: float = 1.0) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def _migration_smoke_skip_reason() -> str | None:
    url = _db_url()
    if not url:
        return "DATABASE_URL/ALEMBIC_DATABASE_URL not set for migration smoke test"
    if not _postgres_reachable(url):
        return (
            "Postgres not reachable for migration smoke test "
            "(start compose postgres or kubectl port-forward svc/spaceops-postgres 5432:5432)"
        )
    return None


_MIGRATION_SMOKE_SKIP = _migration_smoke_skip_reason()


@pytest.mark.skipif(
    _MIGRATION_SMOKE_SKIP is not None,
    reason=_MIGRATION_SMOKE_SKIP or "skipped",
)
def test_alembic_upgrade_downgrade_smoke() -> None:
    env = dict(os.environ)
    env.setdefault("ALEMBIC_DATABASE_URL", _db_url())

    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert upgrade.returncode == 0, upgrade.stderr or upgrade.stdout

    downgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert downgrade.returncode == 0, downgrade.stderr or downgrade.stdout

    reupgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert reupgrade.returncode == 0, reupgrade.stderr or reupgrade.stdout
