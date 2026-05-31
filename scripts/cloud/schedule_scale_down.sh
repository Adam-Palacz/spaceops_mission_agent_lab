#!/usr/bin/env bash
# PS6.9 — resize GKE node pool for overnight scale-down (see docs/runbooks/cloud_cost_hygiene.md).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -n "${PYTHON:-}" ]]; then
  PYTHON_BIN="$PYTHON"
elif [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
elif [[ "${OSTYPE:-}" != linux* && -x "$REPO_ROOT/.venv/Scripts/python.exe" ]]; then
  PYTHON_BIN="$REPO_ROOT/.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  PYTHON_BIN="python"
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/schedule_scale_down.py" "$@"
