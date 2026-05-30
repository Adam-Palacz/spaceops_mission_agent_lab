#!/usr/bin/env python3
"""Run pytest for pre-commit using the active interpreter (avoids Windows PATH issues)."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    return subprocess.call([sys.executable, "-m", "pytest", "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
