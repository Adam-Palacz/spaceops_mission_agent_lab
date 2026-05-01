from __future__ import annotations

import argparse
import json

from apps.replay.workflow import replay_by_run_id


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay a stored run by run_id and compare core outcomes."
    )
    parser.add_argument("--run-id", required=True, help="Original run_id to replay")
    args = parser.parse_args()

    try:
        result = replay_by_run_id(args.run_id)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Replay failed: {exc}")
        return 1
    except Exception as exc:
        print(f"Replay execution error: {exc}")
        return 1

    comparison = result.get("comparison") or {}
    has_diff = bool(comparison.get("has_diff"))
    print(
        json.dumps(
            {
                "run_id": result.get("run_id"),
                "replay_run_id": result.get("replay_run_id"),
                "incident_id": result.get("incident_id"),
                "comparison": comparison,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    if has_diff:
        print("Replay completed with behavior differences.")
        return 2
    print("Replay completed with no core behavior differences.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
