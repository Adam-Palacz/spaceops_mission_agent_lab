from __future__ import annotations

import os
import subprocess
import sys

import pytest


def _db_url() -> str:
    return (
        os.getenv("ALEMBIC_DATABASE_URL", "").strip()
        or os.getenv("DATABASE_URL", "").strip()
    )


@pytest.mark.skipif(
    not _db_url(),
    reason="DATABASE_URL/ALEMBIC_DATABASE_URL not set for migration smoke test",
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
