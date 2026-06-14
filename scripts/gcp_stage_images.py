#!/usr/bin/env python3
"""Build and push api/mcp images to Artifact Registry (PS7.1)."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def resolve_tool(name: str) -> str:
    """Full executable path (Windows needs gcloud.cmd, not bare 'gcloud')."""
    path = shutil.which(name)
    if not path:
        raise SystemExit(
            f"Missing {name} on PATH. Install it or run scripts/refresh_dev_path.ps1 "
            f"in a new terminal."
        )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build/push SpaceOps images to GCP AR")
    parser.add_argument("--tag", default=os.getenv("GCP_IMAGE_TAG", "stage"))
    parser.add_argument("--project", default=os.getenv("GCP_PROJECT_ID", "").strip())
    parser.add_argument("--region", default=os.getenv("GCP_REGION", "us-central1"))
    parser.add_argument(
        "--repository",
        default=os.getenv("GCP_ARTIFACT_REGISTRY_REPOSITORY", "spaceops"),
        help="Artifact Registry repository ID (default: spaceops)",
    )
    parser.add_argument(
        "--skip-repository-check",
        action="store_true",
        help="Skip Artifact Registry existence check before building images.",
    )
    parser.add_argument("--skip-mcp", action="store_true")
    args = parser.parse_args()

    if not args.project:
        raise SystemExit("Set GCP_PROJECT_ID or pass --project")

    gcloud = resolve_tool("gcloud")
    docker = resolve_tool("docker")

    ar_host = f"{args.region}-docker.pkg.dev/{args.project}/{args.repository}"
    registry_host = f"{args.region}-docker.pkg.dev"
    subprocess.run(
        [gcloud, "auth", "configure-docker", registry_host, "--quiet"],
        check=True,
        cwd=REPO_ROOT,
    )

    if not args.skip_repository_check:
        describe = subprocess.run(
            [
                gcloud,
                "artifacts",
                "repositories",
                "describe",
                args.repository,
                "--project",
                args.project,
                "--location",
                args.region,
            ],
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
            check=False,
        )
        if describe.returncode != 0:
            detail = (describe.stderr or describe.stdout or "").strip()
            raise SystemExit(
                "Artifact Registry repository not found or not accessible:\n"
                f"  {ar_host}\n\n"
                "Run Terraform first from infra/terraform/gcp and confirm the output:\n"
                "  terraform apply\n"
                "  terraform output artifact_registry_repository\n\n"
                "If Terraform state is empty, do not run image push yet. If the repo was created "
                "outside Terraform, import it or set GCP_ARTIFACT_REGISTRY_REPOSITORY to the "
                "managed repository ID.\n\n"
                f"gcloud detail:\n{detail}"
            )

    images = [(f"{ar_host}/api:{args.tag}", "apps/api/Dockerfile")]
    if not args.skip_mcp:
        images.append((f"{ar_host}/mcp:{args.tag}", "apps/mcp/Dockerfile"))

    for ref, dockerfile in images:
        print(f"Building {ref} ...")
        subprocess.run(
            [docker, "build", "-t", ref, "-f", dockerfile, "."],
            check=True,
            cwd=REPO_ROOT,
        )
        print(f"Pushing {ref} ...")
        subprocess.run([docker, "push", ref], check=True, cwd=REPO_ROOT)

    print(
        f"\nDone. Helm: --set images.api.repository={ar_host}/api --set images.mcp.repository={ar_host}/mcp --set images.api.tag={args.tag}"
    )


if __name__ == "__main__":
    main()
