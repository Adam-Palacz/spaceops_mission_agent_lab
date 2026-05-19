#!/usr/bin/env python3
"""Golden baseline CLI (PS2.8). Prefer scripts/golden_runner.py for PS4.5 diff artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Standalone CLI: apps.* imports require REPO_ROOT on sys.path first.
from apps.replay.golden import (  # noqa: E402
    GOLDEN_BASELINES_DIR,
    GOLDEN_MANIFEST_PATH,
    check_run_against_baseline,
)
from apps.replay.golden_runner import (  # noqa: E402
    UPDATE_CONFIRM_TOKEN,
    require_update_confirm,
    run_manifest,
    write_report_artifacts,
    refresh_baseline,
)
from apps.replay.workflow import replay_by_run_id  # noqa: E402


def _cmd_check(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    baselines_dir = Path(args.baselines_dir)
    exit_code, report = run_manifest(
        manifest_path, baselines_dir, replay_fn=replay_by_run_id
    )
    if getattr(args, "output_dir", None):
        write_report_artifacts(report, Path(args.output_dir))
    if exit_code == 0:
        print("golden-check: OK (all cases match baselines)")
        return 0
    failures = [c for c in report.get("cases") or [] if c.get("status") != "pass"]
    print(
        json.dumps(
            {"status": "mismatch", "failures": failures}, indent=2, ensure_ascii=False
        )
    )
    print(
        "golden-check: FAILED — replay outcomes differ from baselines", file=sys.stderr
    )
    return exit_code if exit_code != 0 else 2


def _cmd_update(args: argparse.Namespace) -> int:
    try:
        require_update_confirm(getattr(args, "confirm", None))
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
    except (FileNotFoundError, ValueError) as exc:
        print(f"golden-update failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"golden-update execution error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote baseline: {path}")
    print(
        'If this is a new pin, add {"run_id": ...} under cases in '
        f"{args.manifest or GOLDEN_MANIFEST_PATH}"
    )
    return 0


def _cmd_verify_case(args: argparse.Namespace) -> int:
    """Single run_id against an explicit baseline path (used by tests)."""
    path = Path(args.baseline_file)
    ok, detail = check_run_against_baseline(
        args.run_id.strip(), path, replay_fn=replay_by_run_id
    )
    if ok:
        print(json.dumps({"run_id": args.run_id, "status": "ok"}, indent=2))
        return 0
    print(json.dumps({"run_id": args.run_id, "status": "mismatch", **detail}, indent=2))
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden replay baselines (PS2.8)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser(
        "check", help="Replay each pinned run_id and compare to baselines"
    )
    p_check.add_argument(
        "--manifest",
        default=str(GOLDEN_MANIFEST_PATH),
        help="Path to golden_manifest_v1 JSON",
    )
    p_check.add_argument(
        "--baselines-dir",
        default=str(GOLDEN_BASELINES_DIR),
        help="Directory containing run_<run_id>_baseline.json files",
    )
    p_check.add_argument(
        "--output-dir",
        default="",
        help="Optional: write golden_diff_report_v1 artifacts (PS4.5)",
    )
    p_check.set_defaults(func=_cmd_check)

    p_up = sub.add_parser(
        "update",
        help="Run replay once and write expected_outcome from current pipeline output",
    )
    p_up.add_argument("--run-id", required=True)
    p_up.add_argument(
        "--confirm",
        required=True,
        help=f"Required explicit intent: {UPDATE_CONFIRM_TOKEN}",
    )
    p_up.add_argument(
        "--baselines-dir",
        default=str(GOLDEN_BASELINES_DIR),
        help="Where to write run_<run_id>_baseline.json",
    )
    p_up.add_argument(
        "--manifest", default=str(GOLDEN_MANIFEST_PATH), help="Hint path only"
    )
    p_up.add_argument(
        "--case-id", default="", help="Optional logical case id stored in baseline"
    )
    p_up.add_argument("--notes", default="", help="Optional engineer note")
    p_up.set_defaults(func=_cmd_update)

    p_one = sub.add_parser("verify-case", help="Check one baseline file against replay")
    p_one.add_argument("--run-id", required=True)
    p_one.add_argument("--baseline-file", required=True)
    p_one.set_defaults(func=_cmd_verify_case)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
