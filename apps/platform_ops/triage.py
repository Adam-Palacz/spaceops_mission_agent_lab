"""PS7.8 — rule-based + optional LLM platform ops triage."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

CONFIDENCE_ESCALATE_THRESHOLD = 0.55

SAFE_VERIFY_COMMANDS = [
    {
        "kind": "verify",
        "risk": "safe",
        "command": "docker compose ps",
        "description": "Confirm core services are up.",
    },
    {
        "kind": "verify",
        "risk": "safe",
        "command": 'curl "http://localhost:8000/dlq/telemetry?limit=50"',
        "description": "Inspect DLQ sample via API.",
    },
    {
        "kind": "verify",
        "risk": "safe",
        "command": "python -m scripts.platform_ops_triage --collect-only",
        "description": "Refresh platform ops evidence JSON.",
    },
]

APPROVAL_REQUIRED_COMMANDS = [
    {
        "kind": "remediate",
        "risk": "approval_required",
        "command": "python -m scripts.replay_queue --dlq-ids <ids> --apply",
        "description": "Replay DLQ rows (requires --i-approve on platform_ops_triage first).",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def analyze_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Deterministic hypotheses and recommendations from a snapshot fixture or collector."""
    hypotheses: list[dict[str, Any]] = []

    postgres = (snapshot.get("services") or {}).get("postgres") or {}
    if not postgres.get("reachable"):
        hypotheses.append(
            {
                "class": "postgres_unavailable",
                "domain": "queue_dlq",
                "confidence": 0.95,
                "rationale": "Postgres connectivity check failed; DLQ replay and persistence blocked.",
            }
        )

    api = (snapshot.get("services") or {}).get("api") or {}
    if not api.get("reachable"):
        hypotheses.append(
            {
                "class": "api_unavailable",
                "domain": "general",
                "confidence": 0.9,
                "rationale": "API /health probe failed; operator endpoints unavailable.",
            }
        )

    dlq = (snapshot.get("queue") or {}).get("dlq") or {}
    total = int(dlq.get("total_count") or 0) if dlq.get("available") else 0
    if total >= 10:
        top_reason = ""
        counts = dlq.get("reason_counts") or {}
        if counts:
            top_reason = max(counts, key=lambda k: counts[k])
        hypotheses.append(
            {
                "class": "dlq_backlog",
                "domain": "queue_dlq",
                "confidence": 0.85,
                "rationale": f"DLQ has {total} rows; top reason={top_reason or 'unknown'}.",
            }
        )
    elif total > 0:
        hypotheses.append(
            {
                "class": "dlq_entries_present",
                "domain": "queue_dlq",
                "confidence": 0.6,
                "rationale": f"DLQ has {total} rows; monitor trend before replay.",
            }
        )

    mcp = snapshot.get("mcp") or {}
    open_circuits = mcp.get("open_mcp_circuits") or []
    if open_circuits:
        keys = ", ".join(str(c.get("key")) for c in open_circuits)
        hypotheses.append(
            {
                "class": "mcp_breaker_open",
                "domain": "mcp_transport",
                "confidence": 0.88,
                "rationale": f"MCP circuit breaker open: {keys}.",
            }
        )

    unreachable = [
        ep.get("name") for ep in (mcp.get("endpoints") or []) if not ep.get("reachable")
    ]
    if unreachable:
        hypotheses.append(
            {
                "class": "mcp_unreachable",
                "domain": "mcp_transport",
                "confidence": 0.8,
                "rationale": f"MCP endpoints unreachable: {', '.join(str(x) for x in unreachable)}.",
            }
        )

    env = snapshot.get("environment") or {}
    if env.get("nats_url_configured") is False and total > 0:
        hypotheses.append(
            {
                "class": "nats_misconfigured",
                "domain": "queue_dlq",
                "confidence": 0.7,
                "rationale": "NATS_URL not configured while DLQ symptoms present.",
            }
        )

    if not hypotheses:
        hypotheses.append(
            {
                "class": "no_major_signals",
                "domain": "general",
                "confidence": 0.5,
                "rationale": "No critical platform ops signals in snapshot.",
            }
        )

    hypotheses.sort(key=lambda h: (-float(h["confidence"]), str(h["class"])))

    top = hypotheses[0]
    escalate = float(top["confidence"]) < CONFIDENCE_ESCALATE_THRESHOLD

    recommendations = list(SAFE_VERIFY_COMMANDS)
    if any(h["class"] in ("dlq_backlog", "dlq_entries_present") for h in hypotheses):
        recommendations.append(
            {
                "kind": "verify",
                "risk": "safe",
                "command": "python -m scripts.replay_queue --dlq-ids <ids>",
                "description": "Dry-run replay candidate selection (no --apply).",
            }
        )
        recommendations.extend(APPROVAL_REQUIRED_COMMANDS)

    return {
        "analyzed_at": _utc_now(),
        "hypotheses": hypotheses,
        "top_hypothesis": top,
        "escalate_to_human": escalate,
        "recommendations": recommendations,
        "apply_allowed": False,
        "human_decision": None,
    }


def build_triage_report(
    snapshot: dict[str, Any],
    *,
    use_llm: bool = False,
) -> dict[str, Any]:
    analysis = analyze_snapshot(snapshot)
    llm_notes = ""
    if use_llm:
        llm_notes = _optional_llm_summary(snapshot, analysis)

    return {
        "schema_version": snapshot.get("schema_version", "1"),
        "snapshot": snapshot,
        "analysis": analysis,
        "llm_summary": llm_notes or None,
        "audit": {
            "timestamp": _utc_now(),
            "evidence_sources": [
                "services.api",
                "services.postgres",
                "queue.dlq",
                "mcp.endpoints",
                "mcp.circuit_breakers",
            ],
            "suggested_steps": [r["command"] for r in analysis["recommendations"]],
            "human_decision": None,
            "write_actions_executed": False,
        },
    }


def _optional_llm_summary(snapshot: dict[str, Any], analysis: dict[str, Any]) -> str:
    from config import settings

    if not (getattr(settings, "openai_api_key", "") or "").strip():
        return ""
    try:
        from apps.llm_gateway import generate

        top = analysis.get("top_hypothesis") or {}
        prompt = (
            "Summarize this platform ops triage in 2 sentences for an SRE. "
            f"Top hypothesis: {top.get('class')} ({top.get('confidence')}). "
            f"Domains: {snapshot.get('symptom_domains')}. "
            "Do not suggest destructive actions without human approval."
        )
        out = generate(prompt=prompt, node="platform_ops_triage")
        return str(out.get("content") or "").strip()
    except Exception:
        return ""
