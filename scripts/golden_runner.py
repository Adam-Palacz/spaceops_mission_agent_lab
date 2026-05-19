#!/usr/bin/env python3
"""
PS4.5 — Golden runner CLI: run pinned cases, emit diff artifacts, refresh baselines.

Examples (repo root):

  python scripts/golden_runner.py run \\
    --manifest tests/fixtures/golden/manifest.json \\
    --baselines-dir tests/fixtures/golden/baselines \\
    --output-dir data/replay/golden/reports/latest

  python scripts/golden_runner.py update --run-id <uuid> --confirm baseline-update
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Standalone CLI: apps.* imports require REPO_ROOT on sys.path first.
from apps.replay.golden import GOLDEN_BASELINES_DIR, GOLDEN_MANIFEST_PATH  # noqa: E402
from apps.replay.golden_runner import (  # noqa: E402
    UPDATE_CONFIRM_TOKEN,
    require_update_confirm,
    run_manifest,
    write_report_artifacts,
    refresh_baseline,
)
from apps.replay.workflow import replay_by_run_id  # noqa: E402


def _cmd_run(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    baselines_dir = Path(args.baselines_dir)
    exit_code, report = run_manifest(
        manifest_path, baselines_dir, replay_fn=replay_by_run_id
    )
    if args.output_dir:
        out = Path(args.output_dir)
        report_path = write_report_artifacts(report, out)
        print(f"Wrote diff report: {report_path}")
    if exit_code == 0:
        print("golden-runner: PASS (all cases match baselines)")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        print(
            f"golden-runner: FAILED (gate_status={report.get('gate_status')})",
            file=sys.stderr,
        )
    return exit_code


def _cmd_check(args: argparse.Namespace) -> int:
    """Check-only: same as run without requiring output-dir."""
    manifest_path = Path(args.manifest)
    baselines_dir = Path(args.baselines_dir)
    exit_code, report = run_manifest(
        manifest_path, baselines_dir, replay_fn=replay_by_run_id
    )
    out_dir = args.output_dir
    if out_dir:
        write_report_artifacts(report, Path(out_dir))
    if exit_code == 0:
        print("golden-check: OK (all cases match baselines)")
        return 0
    print(json.dumps({"status": "mismatch", "report": report}, indent=2))
    print("golden-check: FAILED", file=sys.stderr)
    return exit_code if exit_code != 0 else 2


def _cmd_update(args: argparse.Namespace) -> int:
    try:
        require_update_confirm(args.confirm)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    run_id = args.run_id.strip()
    if not run_id:
        print("--run-id required", file=sys.stderr)
        return 1
    try:
        path = refresh_baseline(
            run_id,
            Path(args.baselines_dir),
            case_id=args.case_id or "",
            notes=args.notes or "",
            replay_fn=replay_by_run_id,
        )
    except Exception as exc:
        print(f"golden-update failed: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote baseline: {path}")
    print(
        "Committed baseline reflects explicit operator refresh "
        f"(--confirm {UPDATE_CONFIRM_TOKEN})."
    )
    if args.manifest:
        print(f"Ensure cases[] lists run_id in manifest: {args.manifest}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Golden runner — snapshot semantic diffs (PS4.5)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    def _add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--manifest", default=str(GOLDEN_MANIFEST_PATH))
        p.add_argument("--baselines-dir", default=str(GOLDEN_BASELINES_DIR))

    p_run = sub.add_parser("run", help="Execute all cases and optional diff artifacts")
    _add_common(p_run)
    p_run.add_argument(
        "--output-dir",
        default="",
        help="Write report.json and cases/*_diff.json (machine-readable)",
    )
    p_run.set_defaults(func=_cmd_run)

    p_check = sub.add_parser("check", help="Compare replay to baselines (CI gate)")
    _add_common(p_check)
    p_check.add_argument(
        "--output-dir",
        default="",
        help="Optional directory for diff artifacts on failure",
    )
    p_check.set_defaults(func=_cmd_check)

    p_up = sub.add_parser(
        "update",
        help=f"Refresh baseline (requires --confirm {UPDATE_CONFIRM_TOKEN})",
    )
    p_up.add_argument("--run-id", required=True)
    p_up.add_argument(
        "--confirm",
        required=True,
        help=f"Must be exactly: {UPDATE_CONFIRM_TOKEN}",
    )
    p_up.add_argument("--baselines-dir", default=str(GOLDEN_BASELINES_DIR))
    p_up.add_argument("--manifest", default=str(GOLDEN_MANIFEST_PATH))
    p_up.add_argument("--case-id", default="")
    p_up.add_argument("--notes", default="")
    p_up.set_defaults(func=_cmd_update)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
