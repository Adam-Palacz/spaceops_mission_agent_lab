"""
PS4.6 — Behavior metrics for release-readiness dashboards.

Low-cardinality Prometheus counters/histograms: escalation reasons, evidence policy
outcomes, and per-stage latency (p50/p95 via histogram_quantile in Prometheus).
"""

from __future__ import annotations

from typing import Any

from prometheus_client import Counter, Histogram

# Canonical pipeline node names (LangGraph span names in graph._wrap_node).
CANONICAL_STAGES = frozenset(
    {
        "triage",
        "investigate",
        "check_escalation",
        "decide",
        "act",
        "build_report",
    }
)

# Bounded escalation reasons — unknown values map to "other".
CANONICAL_ESCALATION_REASONS = frozenset(
    {
        "no_evidence",
        "conflicting_signals",
        "tool_failure",
        "policy_deny",
        "prompt_injection_detected",
        "evidence_policy_violation",
        "output_schema_violation",
        "token_limit",
        "rate_limit",
        "llm_timeout",
        "llm_provider_error",
        "budget_exceeded",
        "run_timeout",
        "other",
    }
)

CANONICAL_EVIDENCE_POLICY_STATUSES = frozenset(
    {"ok", "violation", "skipped_escalated", "unknown"}
)

CANONICAL_TOOL_NAMES = frozenset(
    {
        "query_telemetry",
        "search_runbooks",
        "search_postmortems",
        "create_ticket",
        "create_pr",
        "opa_check",
        "other",
    }
)

CANONICAL_TOOL_OUTCOMES = frozenset({"success", "empty", "failure"})

AGENT_BEHAVIOR_RUNS_TOTAL = Counter(
    "agent_behavior_runs_total",
    "Agent runs by behavioral outcome (PS4.6). Use for escalation rate denominators.",
    ["outcome"],
)

AGENT_ESCALATIONS_TOTAL = Counter(
    "agent_escalations_total",
    "Escalations by canonical reason (PS4.6). Incremented once per escalated run.",
    ["reason"],
)

AGENT_EVIDENCE_COVERAGE_TOTAL = Counter(
    "agent_evidence_coverage_total",
    "Runs by evidence policy status and whether citations were present (PS4.6).",
    ["policy_status", "has_citations"],
)

AGENT_TOOL_OUTCOME_TOTAL = Counter(
    "agent_tool_outcome_total",
    "Per-tool outcomes from investigation tool_outcomes and act_results (PS4.6).",
    ["tool", "outcome"],
)

AGENT_STAGE_DURATION_SECONDS = Histogram(
    "agent_stage_duration_seconds",
    "Per-pipeline-node wall time in seconds from stage_timings (PS4.6).",
    ["stage"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)


def normalize_escalation_reason(reason: str | None) -> str:
    value = (reason or "").strip().lower()[:64]
    if value in CANONICAL_ESCALATION_REASONS:
        return value
    return "other"


def normalize_stage(node: str | None) -> str:
    value = (node or "").strip().lower()
    if value in CANONICAL_STAGES:
        return value
    return "other"


def normalize_tool_name(tool: str | None) -> str:
    value = (tool or "").strip().lower()[:64]
    if value in CANONICAL_TOOL_NAMES:
        return value
    return "other"


def normalize_tool_outcome(outcome: str | None) -> str:
    value = (outcome or "").strip().lower()
    if value in CANONICAL_TOOL_OUTCOMES:
        return value
    return "other"


def normalize_evidence_policy_status(status: str | None) -> str:
    value = (status or "").strip().lower()
    if value in CANONICAL_EVIDENCE_POLICY_STATUSES:
        return value
    return "unknown"


def record_agent_run_behavior(result: dict[str, Any], duration_seconds: float) -> None:
    """
    Emit PS4.6 behavior metrics after a successful pipeline invocation.

    ``result`` is the final agent state dict from run_pipeline.
    """
    del (
        duration_seconds
    )  # reserved for future correlation; S2.9 tracks wall clock at API.

    escalated = bool(result.get("escalated"))
    outcome = "escalated" if escalated else "completed"
    AGENT_BEHAVIOR_RUNS_TOTAL.labels(outcome=outcome).inc()

    if escalated:
        packet = result.get("escalation_packet") or {}
        reason = normalize_escalation_reason(
            packet.get("reason") if isinstance(packet, dict) else None
        )
        AGENT_ESCALATIONS_TOTAL.labels(reason=reason).inc()

    policy_status = normalize_evidence_policy_status(
        str(result.get("evidence_policy_status") or "")
    )
    citations = result.get("citations") or []
    has_citations = (
        "true" if isinstance(citations, list) and len(citations) > 0 else "false"
    )
    AGENT_EVIDENCE_COVERAGE_TOTAL.labels(
        policy_status=policy_status,
        has_citations=has_citations,
    ).inc()

    tool_outcomes = result.get("tool_outcomes") or {}
    if isinstance(tool_outcomes, dict):
        for tool, outcome in tool_outcomes.items():
            AGENT_TOOL_OUTCOME_TOTAL.labels(
                tool=normalize_tool_name(str(tool)),
                outcome=normalize_tool_outcome(str(outcome)),
            ).inc()
    for entry in result.get("act_results") or []:
        if not isinstance(entry, dict):
            continue
        AGENT_TOOL_OUTCOME_TOTAL.labels(
            tool=normalize_tool_name(str(entry.get("tool") or "")),
            outcome=normalize_tool_outcome(str(entry.get("outcome") or "")),
        ).inc()

    for entry in result.get("stage_timings") or []:
        if not isinstance(entry, dict):
            continue
        stage = normalize_stage(str(entry.get("node") or ""))
        if stage == "other":
            continue
        try:
            duration_ms = int(entry.get("duration_ms") or 0)
        except (TypeError, ValueError):
            duration_ms = 0
        seconds = max(0.0, duration_ms / 1000.0)
        AGENT_STAGE_DURATION_SECONDS.labels(stage=stage).observe(seconds)


def record_agent_run_error(duration_seconds: float) -> None:
    """Emit behavior metrics when the pipeline fails before returning state."""
    del duration_seconds
    AGENT_BEHAVIOR_RUNS_TOTAL.labels(outcome="error").inc()
