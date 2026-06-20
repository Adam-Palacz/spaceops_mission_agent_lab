"""
Queue-driven agent graph worker (PS7.3 Variant A).

Run: ``python -m apps.workers.agent_graph`` (requires Postgres + checkpoint enabled).

Claims jobs from ``agent_run_queue``, executes ``run_pipeline`` with durable checkpoints,
and completes/fails queue rows. Expired leases are reclaimed (worker kill → resume).
"""

from __future__ import annotations

import logging
import os
import socket
import sys
import time

from apps.agent.checkpointing import durable_checkpoint_enabled, load_checkpoint
from apps.agent.graph import run_pipeline
from apps.agent.run_queue import RunQueueJob, claim_next_job, complete_job, fail_job
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _worker_id() -> str:
    return (
        os.getenv("AGENT_WORKER_ID") or socket.gethostname() or "agent-worker"
    ).strip()


def process_job(job: RunQueueJob) -> None:
    """Execute one claimed queue job with idempotency guard."""
    worker_id = job.worker_id or _worker_id()
    cp = load_checkpoint(job.run_id)
    if cp and cp.status == "completed":
        logger.info("run_id=%s already completed in checkpoint — skipping", job.run_id)
        if not complete_job(job.run_id, worker_id=worker_id):
            logger.warning(
                "run_id=%s completion skipped; lease owner changed", job.run_id
            )
        return

    resume = job.resume or bool(cp and cp.status == "in_progress" and cp.next_node)
    result = run_pipeline(
        job.incident_id,
        job.payload,
        replay_source=job.replay_source,
        run_id=job.run_id,
        resume=resume,
    )
    logger.info(
        "run_id=%s incident_id=%s escalated=%s",
        job.run_id,
        job.incident_id,
        bool(result.get("escalated")),
    )
    if not complete_job(job.run_id, worker_id=worker_id):
        logger.warning("run_id=%s completion skipped; lease owner changed", job.run_id)


def run_once(*, worker_id: str | None = None) -> bool:
    """Claim and process at most one job. Returns True if a job was processed."""
    wid = worker_id or _worker_id()
    job = claim_next_job(worker_id=wid)
    if not job:
        return False
    try:
        process_job(job)
    except Exception as exc:
        logger.exception("run_id=%s failed: %s", job.run_id, exc)
        fail_job(job.run_id, str(exc), worker_id=job.worker_id or wid)
        raise
    return True


def run_forever() -> None:
    if not durable_checkpoint_enabled():
        logger.error(
            "AGENT_DURABLE_CHECKPOINT_ENABLED must be true on the worker (Variant A)."
        )
        sys.exit(1)

    poll = float(getattr(settings, "agent_run_queue_poll_seconds", 1.0))
    wid = _worker_id()
    logger.info("Agent graph worker started id=%s poll=%.1fs", wid, poll)

    while True:
        try:
            if run_once(worker_id=wid):
                continue
        except Exception:
            pass
        time.sleep(max(0.1, poll))


def main() -> None:
    run_forever()


if __name__ == "__main__":
    main()
