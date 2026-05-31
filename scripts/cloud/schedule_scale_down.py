#!/usr/bin/env python3
"""PS6.9 GKE node pool scale-down / scale-up stub (non-prod cost hygiene)."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Resize a GKE node pool for overnight scale-down (PS6.9)."
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print gcloud command without executing.",
    )
    p.add_argument(
        "--project",
        default=os.getenv("GCP_PROJECT_ID", ""),
        help="GCP project ID (env GCP_PROJECT_ID).",
    )
    p.add_argument(
        "--region",
        default=os.getenv("GCP_REGION", "us-central1"),
        help="Cluster region (env GCP_REGION).",
    )
    p.add_argument(
        "--cluster",
        default=os.getenv("GKE_CLUSTER", "spaceops-stage"),
        help="GKE cluster name (env GKE_CLUSTER).",
    )
    p.add_argument(
        "--node-pool",
        default=os.getenv("GKE_NODE_POOL", "spaceops-stage-pool"),
        help="Node pool name (env GKE_NODE_POOL).",
    )
    p.add_argument(
        "--nodes",
        type=int,
        default=int(os.getenv("GKE_TARGET_NODES", "0") or 0),
        help="Target node count (default 0 = scale down).",
    )
    return p.parse_args()


def build_gcloud_command(args: argparse.Namespace) -> list[str]:
    if not args.project:
        raise SystemExit(
            "Missing --project or GCP_PROJECT_ID. See docs/runbooks/cloud_cost_hygiene.md"
        )
    return [
        "gcloud",
        "container",
        "clusters",
        "resize",
        args.cluster,
        "--node-pool",
        args.node_pool,
        "--num-nodes",
        str(args.nodes),
        "--region",
        args.region,
        "--project",
        args.project,
        "--quiet",
    ]


def main() -> int:
    args = _parse_args()
    cmd = build_gcloud_command(args)
    printable = shlex.join(cmd)
    print(f"target_nodes={args.nodes}")
    print(f"cluster={args.cluster}")
    print(f"node_pool={args.node_pool}")
    print(f"region={args.region}")
    print(f"project={args.project}")
    if args.dry_run:
        print(f"would_run={printable}")
        return 0
    print(f"running={printable}")
    subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
