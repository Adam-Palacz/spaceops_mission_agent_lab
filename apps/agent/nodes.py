"""
SpaceOps Agent — pipeline nodes: Triage, Investigate, Decide, Report (S1.7).
Uses OpenAI Chat Completions API via httpx (avoids LangChain/Pydantic BaseCache issue).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config import settings
from apps.agent.state import AgentState, Citation, EscalationPacket
from apps.agent.mcp_client import (
    call_telemetry,
    call_search_runbooks,
    call_search_postmortems,
    call_create_ticket,
    call_create_pr,
    signature_from_payload,
)
from apps.agent.audit_log import append_entry as audit_append
from apps.agent.opa_client import opa_allow
from apps.agent.approval_store import create as approval_store_create
from apps.llm_observability import start_llm_run, log_llm_call
from apps.llm_gateway import (
    LLMGatewayProviderError,
    LLMGatewayTimeoutError,
    generate as gateway_generate,
)
from apps.telemetry import get_tracer
from apps.tracing import is_valid_trace_id_hex
from opentelemetry.trace import SpanKind, Status, StatusCode
from prompts.registry import (
    DECIDE_PROMPT_ID,
    TRIAGE_PROMPT_ID,
    get_prompt,
)
from apps.contracts.output_validation import (
    OUTPUT_SCHEMA_VIOLATION,
    OutputSchemaViolation,
    escalation_packet_for_schema_violation,
    validate_act_results,
    validate_approval_requests,
    validate_escalation_packet,
    validate_run_report,
)
from apps.agent.prompt_injection import (
    PROMPT_INJECTION_DETECTED,
    format_detection_detail,
    has_critical_injection,
    merge_detection_codes,
    sanitize_investigation_notes,
    sanitize_payload_for_prompt,
    scan_citations_and_hypotheses,
    validate_plan_allowlist,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_INCIDENTS = REPO_ROOT / "data" / "incidents"

_SUBSYSTEMS = ("ADCS", "Power", "Thermal", "Comms", "Payload", "Ground")


def _tool_outcomes_compact(tool_outcomes: object, *, max_len: int = 200) -> str:
    """Serialize tool_outcomes for span tags (bounded, low cardinality)."""
    if not isinstance(tool_outcomes, dict):
        return ""
    parts: list[str] = []
    for key in sorted(tool_outcomes.keys()):
        val = tool_outcomes.get(key)
        parts.append(f"{key}={val}")
    out = ";".join(parts)
    return out if len(out) <= max_len else out[: max_len - 3] + "..."


def annotate_span_with_observability_attrs(span, state: AgentState) -> None:
    """Low-cardinality pipeline facts on the current node span (no payloads or secrets)."""
    rid = state.get("run_id")
    if isinstance(rid, str) and rid.strip():
        span.set_attribute("run_id", rid.strip()[:64])
    sub = state.get("subsystem")
    if isinstance(sub, str) and sub.strip():
        span.set_attribute("subsystem", sub.strip()[:32])
    risk = state.get("risk")
    if isinstance(risk, str) and risk.strip():
        span.set_attribute("risk", risk.strip()[:16])
    citations = state.get("citations") or []
    if isinstance(citations, list):
        span.set_attribute("citation_count", len(citations))
    span.set_attribute("escalated", bool(state.get("escalated")))
    packet = state.get("escalation_packet") or {}
    if isinstance(packet, dict):
        reason = packet.get("reason")
        if isinstance(reason, str) and reason.strip():
            span.set_attribute("escalation_reason", reason.strip()[:64])
    compact = _tool_outcomes_compact(state.get("tool_outcomes"))
    if compact:
        span.set_attribute("tool_outcomes", compact)
    eps = state.get("evidence_policy_status")
    if isinstance(eps, str) and eps.strip():
        span.set_attribute("evidence_policy_status", eps.strip()[:32])
    epr = state.get("evidence_policy_reason")
    if isinstance(epr, str) and epr.strip():
        span.set_attribute("evidence_policy_reason", epr.strip()[:64])
    oss = state.get("output_schema_status")
    if isinstance(oss, str) and oss.strip():
        span.set_attribute("output_schema_status", oss.strip()[:32])
    osr = state.get("output_schema_reason")
    if isinstance(osr, str) and osr.strip():
        span.set_attribute("output_schema_reason", osr.strip()[:64])
    igs = state.get("injection_guard_status")
    if isinstance(igs, str) and igs.strip():
        span.set_attribute("injection_guard_status", igs.strip()[:32])
    igr = state.get("injection_guard_reason")
    if isinstance(igr, str) and igr.strip():
        span.set_attribute("injection_guard_reason", igr.strip()[:64])
    plan = state.get("plan")
    if isinstance(plan, list) and plan:
        span.set_attribute("plan_step_count", len(plan))
        types: set[str] = set()
        for step in plan:
            if isinstance(step, dict):
                t = (step.get("action_type") or "").strip().lower()
                if t:
                    types.add(t)
        if types:
            span.set_attribute("plan_action_types", ",".join(sorted(types))[:128])


def emit_decision_summary_span(state: AgentState, *, phase: str) -> None:
    """
    One semantic summary span after escalation check / decide (Jaeger-friendly, low cardinality).
    Full narrative stays in audit / LLM logs.
    """
    tracer = get_tracer("apps.agent")
    incident_id = str(state.get("incident_id") or "unknown")[:64]
    run_id = str(state.get("run_id") or "")[:64]
    escalated = bool(state.get("escalated"))
    packet = state.get("escalation_packet") or {}
    reason = (
        str(packet.get("reason") or "").strip()[:64] if isinstance(packet, dict) else ""
    )
    subsystem = str(state.get("subsystem") or "")[:32]
    risk = str(state.get("risk") or "")[:16]
    citations = state.get("citations") or []
    citation_count = len(citations) if isinstance(citations, list) else 0
    outcomes_s = _tool_outcomes_compact(state.get("tool_outcomes"))
    plan = state.get("plan") or []
    plan_step_count = len(plan) if isinstance(plan, list) else 0
    types: set[str] = set()
    if isinstance(plan, list):
        for step in plan:
            if isinstance(step, dict):
                t = (step.get("action_type") or "").strip().lower()
                if t:
                    types.add(t)
    plan_types = ",".join(sorted(types))[:128]

    parts = [
        f"phase={phase}",
        f"esc={escalated}",
        f"reason={reason or 'none'}",
        f"sub={subsystem or 'none'}",
        f"risk={risk or 'none'}",
        f"cit={citation_count}",
        f"tools={outcomes_s or 'none'}",
    ]
    if phase == "post_decide":
        parts.append(f"steps={plan_step_count}")
        parts.append(f"types={plan_types or 'none'}")
    summary_line = "|".join(parts)
    if len(summary_line) > 256:
        summary_line = summary_line[:253] + "..."

    with tracer.start_as_current_span(
        "agent.decision_summary", kind=SpanKind.INTERNAL
    ) as sp:
        sp.set_attribute("agent.phase", phase)
        sp.set_attribute("incident_id", incident_id)
        if run_id:
            sp.set_attribute("run_id", run_id)
        sp.set_attribute("escalated", escalated)
        if reason:
            sp.set_attribute("escalation_reason", reason)
        if subsystem:
            sp.set_attribute("subsystem", subsystem)
        if risk:
            sp.set_attribute("risk", risk)
        sp.set_attribute("citation_count", citation_count)
        if outcomes_s:
            sp.set_attribute("tool_outcomes", outcomes_s)
        if phase == "post_decide":
            sp.set_attribute("plan_step_count", plan_step_count)
            if plan_types:
                sp.set_attribute("plan_action_types", plan_types)
        sp.set_attribute("decision.summary_line", summary_line)


def _audit_schema_guardrail(
    *,
    trace_id: str,
    incident_id: str,
    envelope: str,
    detail: str,
) -> None:
    audit_append(
        trace_id=trace_id,
        incident_id=incident_id,
        actor="agent",
        tool="guardrail_escalation",
        args={
            "reason": OUTPUT_SCHEMA_VIOLATION,
            "envelope": envelope,
            "detail": detail[:200],
        },
        decision="escalate",
        outcome="success",
    )


def _ensure_escalation_packet(
    incident_id: str,
    packet: dict,
    *,
    trace_id: str,
    audit_on_fallback: bool = True,
) -> dict:
    """Validate escalation packet; on failure return a schema-safe fail-closed packet."""
    try:
        return validate_escalation_packet(packet)
    except OutputSchemaViolation as exc:
        if audit_on_fallback:
            _audit_schema_guardrail(
                trace_id=trace_id,
                incident_id=incident_id,
                envelope=exc.envelope,
                detail=exc.operator_message,
            )
        return escalation_packet_for_schema_violation(
            incident_id,
            envelope=exc.envelope,
            detail=exc.operator_message,
        )


def _audit_prompt_injection(
    *,
    trace_id: str,
    incident_id: str,
    source: str,
    codes: list[str],
) -> None:
    audit_append(
        trace_id=trace_id,
        incident_id=incident_id,
        actor="agent",
        tool="prompt_injection_guard",
        args={
            "reason": PROMPT_INJECTION_DETECTED,
            "source": source[:64],
            "detection_codes": codes[:20],
        },
        decision="escalate",
        outcome="success",
    )


def _escalation_for_prompt_injection(
    incident_id: str,
    *,
    detail: str,
    codes: list[str],
) -> dict:
    """PS4.3: fail-closed escalation when untrusted input matches injection patterns."""
    packet: EscalationPacket = {
        "reason": PROMPT_INJECTION_DETECTED,
        "what_we_know": [
            f"Incident {incident_id}",
            "Untrusted payload or evidence contained blocked instruction patterns.",
            detail,
        ],
        "what_we_dont_know": [
            "Whether proposed actions reflect legitimate operator intent.",
        ],
        "what_to_check": [
            "Review raw payload, KB snippets, and audit prompt_injection_guard entries.",
            "Re-run after sanitizing or removing poisoned knowledge-base documents.",
        ],
    }
    return {
        "escalated": True,
        "escalation_packet": packet,
        "injection_guard_status": "violation",
        "injection_guard_reason": PROMPT_INJECTION_DETECTED,
        "injection_detection_codes": codes,
    }


def _escalation_for_limit_or_timeout(
    incident_id: str, reason: str, detail: str
) -> dict:
    """S1.12: build state delta for token_limit, rate_limit or timeout escalation (NF6, F10)."""
    packet: EscalationPacket = {
        "reason": reason,
        "what_we_know": [f"Incident {incident_id}", detail],
        "what_we_dont_know": ["Run did not complete; limit or timeout was hit."],
        "what_to_check": [
            "Review incident payload and consider increasing limits or retrying.",
            "Check agent_run_timeout_seconds, agent_token_budget_per_run, agent_llm_call_timeout_seconds, agent_max_llm_calls_per_run in config.",
        ],
    }
    return {"escalated": True, "escalation_packet": packet}


def _safe_error_message(exc: Exception, max_length: int = 200) -> str:
    """
    Build a short, safe error string for audit log.

    No stack traces or PII; just exception class and message, truncated.
    """
    msg = f"{exc.__class__.__name__}: {exc}"
    # Replace newlines to keep audit entries single-line JSON
    msg = msg.replace("\r", " ").replace("\n", " ")
    if len(msg) > max_length:
        msg = msg[: max_length - 3] + "..."
    return msg


def _is_conflicting_signals(hypotheses: list[str]) -> bool:
    """Detect contradictory evidence cues inside hypotheses text."""
    if not hypotheses:
        return False
    text = " ".join(hypotheses).lower()
    anomaly_markers = (
        "anomaly",
        "degraded",
        "degradation",
        "high",
        "spike",
        "error",
        "critical",
        "drop",
    )
    nominal_markers = (
        "normal",
        "nominal",
        "within limits",
        "stable",
        "healthy",
        "ok",
    )
    has_anomaly = any(token in text for token in anomaly_markers)
    has_nominal = any(token in text for token in nominal_markers)
    return has_anomaly and has_nominal


def _chat_completion(
    prompt: str, model: str | None = None, temperature: float = 0
) -> tuple[str, int]:
    """
    Call OpenAI Chat Completions API. Return (content, total_tokens).
    S1.12: uses agent_llm_call_timeout_seconds; raises httpx.TimeoutException on timeout.
    """
    result = gateway_generate(
        prompt=prompt,
        node="nodes.chat_completion",
        model_id=model,
        temperature=temperature,
    )
    return str(result.get("content") or ""), int(
        (result.get("usage") or {}).get("total_tokens") or 0
    )


def triage(state: AgentState) -> dict:
    """Classify subsystem and risk; persist incident record. S1.12: token budget, rate limit, LLM timeout → escalate."""
    incident_id = state.get("incident_id") or "unknown"
    trace_id = state.get("trace_id") or incident_id
    run_id = state.get("run_id") or trace_id
    payload = state.get("payload") or {}
    tokens_used = state.get("tokens_used") or 0
    llm_calls_used = state.get("llm_calls_used") or 0
    token_budget = max(0, getattr(settings, "agent_token_budget_per_run", 0))
    max_llm_calls = max(0, getattr(settings, "agent_max_llm_calls_per_run", 0))
    if token_budget and tokens_used >= token_budget:
        return _escalation_for_limit_or_timeout(
            incident_id,
            "token_limit",
            f"Token budget ({token_budget}) already reached before triage.",
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    if max_llm_calls and llm_calls_used >= max_llm_calls:
        return _escalation_for_limit_or_timeout(
            incident_id,
            "rate_limit",
            f"Max LLM calls per run ({max_llm_calls}) already reached before triage.",
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    # S3.0: ensure we have a logical run_id for LLM observability.
    run_id = start_llm_run(
        run_id,
        incident_id=incident_id,
        node="triage",
    )
    payload_for_prompt, payload_codes = sanitize_payload_for_prompt(
        payload if isinstance(payload, dict) else {}
    )
    if has_critical_injection(payload_codes):
        _audit_prompt_injection(
            trace_id=trace_id,
            incident_id=incident_id,
            source="payload",
            codes=payload_codes,
        )
        return _escalation_for_prompt_injection(
            incident_id,
            detail=format_detection_detail(payload_codes, extra="payload pre-triage"),
            codes=payload_codes,
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    triage_prompt = get_prompt(TRIAGE_PROMPT_ID)
    prompt = triage_prompt.text.format(
        payload=payload_for_prompt,
        subsystems=", ".join(_SUBSYSTEMS),
    )
    try:
        from apps.model_selection import get_current_model_id

        model_id = get_current_model_id()
        gateway_result = gateway_generate(
            prompt=prompt,
            node="triage",
            model_id=model_id,
            temperature=0,
        )
        content = str(gateway_result.get("content") or "")
        usage_meta = gateway_result.get("usage") or {}
        usage = int(usage_meta.get("total_tokens") or 0)
    except LLMGatewayTimeoutError:
        return _escalation_for_limit_or_timeout(
            incident_id, "llm_timeout", "LLM call timed out during triage."
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    except LLMGatewayProviderError as exc:
        return _escalation_for_limit_or_timeout(
            incident_id,
            "llm_provider_error",
            f"LLM provider error during triage: {exc}",
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    tokens_used += usage
    llm_calls_used += 1
    if token_budget and tokens_used > token_budget:
        return _escalation_for_limit_or_timeout(
            incident_id,
            "token_limit",
            f"Token budget ({token_budget}) exceeded during triage (used {tokens_used}).",
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    # S3.0: record LLM call in observability spine.
    log_llm_call(
        run_id,
        node="triage",
        model_id=model_id,
        prompt_id=triage_prompt.id,
        prompt_version=triage_prompt.version,
        tags={"subsystems": list(_SUBSYSTEMS)},
        metrics={
            "tokens_used": usage,
            "prompt_tokens": int(usage_meta.get("prompt_tokens") or 0),
            "completion_tokens": int(usage_meta.get("completion_tokens") or 0),
            "latency_ms": int(gateway_result.get("latency_ms") or 0),
        },
    )
    text = content.strip().split()
    subsystem = text[0] if len(text) >= 1 else "Ground"
    risk = text[1] if len(text) >= 2 else "medium"
    if subsystem not in _SUBSYSTEMS:
        subsystem = "Ground"
    # Persist incident record
    DATA_INCIDENTS.mkdir(parents=True, exist_ok=True)
    record = {
        "incident_id": incident_id,
        "subsystem": subsystem,
        "risk": risk,
        "payload": payload,
        "triaged_at": datetime.now(timezone.utc).isoformat(),
    }
    out_file = DATA_INCIDENTS / f"incident_{incident_id}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return {
        "subsystem": subsystem,
        "risk": risk,
        "tokens_used": tokens_used,
        "llm_calls_used": llm_calls_used,
        "injection_detection_codes": payload_codes,
        "injection_guard_status": "ok",
        "injection_guard_reason": "",
    }


def investigate(state: AgentState) -> dict:
    """Call Telemetry and KB MCPs; attach hypotheses and citations. S1.9: audit each tool call."""
    payload = state.get("payload") or {}
    subsystem = state.get("subsystem") or "Ground"
    query = signature_from_payload(payload) or subsystem.lower()
    incident_id = state.get("incident_id") or "unknown"
    trace_id = state.get("trace_id") or incident_id
    # Time range from payload or default window
    start = payload.get("time_range_start") or "2025-02-14T09:00:00Z"
    end = payload.get("time_range_end") or "2025-02-14T11:00:00Z"
    channels = payload.get("channels")
    # Tool call + audit (S1.9) + span per tool (S1.10)
    tracer = get_tracer("apps.agent")
    telemetry_args = {
        "time_range_start": start,
        "time_range_end": end,
        "channels": channels if isinstance(channels, list) else [],
    }
    with tracer.start_as_current_span("mcp.query_telemetry") as sp:
        sp.set_attribute("incident_id", incident_id)
        try:
            telemetry = call_telemetry(
                start, end, channels if isinstance(channels, list) else None
            )
            telemetry_error: str | None = None
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised via monkeypatch in tests
            telemetry = []
            telemetry_error = _safe_error_message(exc)
    if telemetry_error:
        telemetry_outcome = "failure"
    elif telemetry:
        telemetry_outcome = "success"
    else:
        telemetry_outcome = "empty"
    audit_append(
        trace_id=trace_id,
        incident_id=incident_id,
        actor="agent",
        tool="query_telemetry",
        args=telemetry_args,
        outcome=telemetry_outcome,
        error_message=telemetry_error,
    )

    runbooks_args = {"query": query, "limit": 5}
    with tracer.start_as_current_span("mcp.search_runbooks") as sp:
        sp.set_attribute("incident_id", incident_id)
        try:
            runbooks = call_search_runbooks(query, 5)
            runbooks_error: str | None = None
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised via monkeypatch in tests
            runbooks = []
            runbooks_error = _safe_error_message(exc)
    if runbooks_error:
        runbooks_outcome = "failure"
    elif runbooks:
        runbooks_outcome = "success"
    else:
        runbooks_outcome = "empty"
    audit_append(
        trace_id=trace_id,
        incident_id=incident_id,
        actor="agent",
        tool="search_runbooks",
        args=runbooks_args,
        outcome=runbooks_outcome,
        error_message=runbooks_error,
    )

    postmortems_args = {"signature": query, "limit": 5}
    with tracer.start_as_current_span("mcp.search_postmortems") as sp:
        sp.set_attribute("incident_id", incident_id)
        try:
            postmortems = call_search_postmortems(query, 5)
            postmortems_error: str | None = None
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised via monkeypatch in tests
            postmortems = []
            postmortems_error = _safe_error_message(exc)
    if postmortems_error:
        postmortems_outcome = "failure"
    elif postmortems:
        postmortems_outcome = "success"
    else:
        postmortems_outcome = "empty"
    audit_append(
        trace_id=trace_id,
        incident_id=incident_id,
        actor="agent",
        tool="search_postmortems",
        args=postmortems_args,
        outcome=postmortems_outcome,
        error_message=postmortems_error,
    )
    hypotheses: list[str] = []
    citations: list[Citation] = []
    if telemetry:
        hypotheses.append(
            f"Telemetry: {len(telemetry)} samples in range; review for anomalies."
        )
        for i, r in enumerate(telemetry[:5]):
            citations.append(
                {
                    "snippet_id": f"telemetry_{i}",
                    "content": str(r),
                    "doc_id": "telemetry",
                }
            )
    for chunk in runbooks:
        if isinstance(chunk, dict) and chunk.get("doc_id"):
            hypotheses.append(f"Runbook: {chunk.get('content', '')[:200]}...")
            citations.append(
                {
                    "doc_id": chunk.get("doc_id", ""),
                    "content": chunk.get("content", ""),
                    "snippet_id": f"runbook_{chunk.get('doc_id', '')}",
                }
            )
    for chunk in postmortems:
        if isinstance(chunk, dict) and chunk.get("doc_id"):
            hypotheses.append(f"Postmortem: {chunk.get('content', '')[:200]}...")
            citations.append(
                {
                    "doc_id": chunk.get("doc_id", ""),
                    "content": chunk.get("content", ""),
                    "snippet_id": f"postmortem_{chunk.get('doc_id', '')}",
                }
            )
    if not hypotheses:
        hypotheses.append("No telemetry or KB hits; escalate for manual review.")
    evidence_codes = scan_citations_and_hypotheses(hypotheses, citations)
    injection_codes = merge_detection_codes(
        list(state.get("injection_detection_codes") or []), evidence_codes
    )
    if evidence_codes:
        _audit_prompt_injection(
            trace_id=trace_id,
            incident_id=incident_id,
            source="investigate_evidence",
            codes=evidence_codes,
        )
    return {
        "hypotheses": hypotheses,
        "citations": citations,
        "tool_outcomes": {
            "query_telemetry": telemetry_outcome,
            "search_runbooks": runbooks_outcome,
            "search_postmortems": postmortems_outcome,
        },
        "injection_detection_codes": injection_codes,
        "injection_guard_status": "ok",
        "injection_guard_reason": "",
    }


def _should_escalate(state: AgentState) -> tuple[bool, str]:
    """Return (escalate, reason). Conditions: no evidence, high risk + no citations, conflicting signals (F10)."""
    hypotheses = state.get("hypotheses") or []
    citations = state.get("citations") or []
    risk = (state.get("risk") or "").lower()
    tool_outcomes = state.get("tool_outcomes") or {}
    if isinstance(tool_outcomes, dict) and any(
        str(v).strip().lower() == "failure" for v in tool_outcomes.values()
    ):
        return True, "tool_failure"

    # No evidence: only the fallback "No telemetry or KB hits" or no citations
    no_evidence = not citations or (
        len(hypotheses) == 1 and "No telemetry or KB hits" in (hypotheses[0] or "")
    )
    if no_evidence:
        return True, "no_evidence"
    # High risk with no supporting citations
    if risk == "high" and len(citations) == 0:
        return True, "high_risk_no_evidence"
    # Conflicting signals in evidence/hypotheses.
    if _is_conflicting_signals(hypotheses):
        return True, "conflicting_signals"
    return False, ""


def check_escalation(state: AgentState) -> dict:
    """S1.8: Evaluate escalation conditions; if met, set escalation_packet (F10). S1.12: preserve limit/timeout escalation."""
    incident_id = state.get("incident_id") or "unknown"
    trace_id = state.get("trace_id") or incident_id
    injection_codes = list(state.get("injection_detection_codes") or [])
    if has_critical_injection(injection_codes) and not state.get("escalated"):
        _audit_prompt_injection(
            trace_id=trace_id,
            incident_id=incident_id,
            source="check_escalation",
            codes=injection_codes,
        )
        packet = _escalation_for_prompt_injection(
            incident_id,
            detail=format_detection_detail(injection_codes),
            codes=injection_codes,
        )
        packet["escalation_packet"] = _ensure_escalation_packet(
            incident_id,
            packet["escalation_packet"],
            trace_id=trace_id,
            audit_on_fallback=False,
        )
        return packet
    # Preserve escalation already set by token_limit, llm_timeout, or run_timeout (NF6)
    if state.get("escalated") and state.get("escalation_packet", {}).get("reason") in (
        "token_limit",
        "rate_limit",
        "llm_timeout",
        "llm_provider_error",
        "run_timeout",
    ):
        packet = _ensure_escalation_packet(
            incident_id,
            state.get("escalation_packet") or {},
            trace_id=trace_id,
            audit_on_fallback=True,
        )
        return {
            "escalated": True,
            "escalation_packet": packet,
            "output_schema_status": "ok"
            if packet.get("reason") != OUTPUT_SCHEMA_VIOLATION
            else "violation",
            "output_schema_reason": ""
            if packet.get("reason") != OUTPUT_SCHEMA_VIOLATION
            else OUTPUT_SCHEMA_VIOLATION,
        }
    escalated, reason = _should_escalate(state)
    if not escalated:
        return {"escalated": False, "escalation_packet": {}}
    incident_id = state.get("incident_id") or "unknown"
    subsystem = state.get("subsystem") or ""
    risk = state.get("risk") or ""
    hypotheses = state.get("hypotheses") or []
    citations = state.get("citations") or []
    packet: EscalationPacket = {
        "reason": reason,
        "what_we_know": [
            f"Incident {incident_id}",
            f"Subsystem: {subsystem}, risk: {risk}",
            f"Investigation produced {len(hypotheses)} note(s), {len(citations)} citation(s).",
        ],
        "what_we_dont_know": [
            "Root cause not confirmed (insufficient evidence or conflicting signals).",
            "Recommend manual review of telemetry and ground logs for the time window.",
        ],
        "what_to_check": [
            "Verify time range and channels in payload match ingested data.",
            "Check MCP Telemetry and KB servers are running if expecting runbook/postmortem hits.",
            "Review raw telemetry and events for the incident window.",
        ],
    }
    if reason == "no_evidence":
        packet["what_we_dont_know"] = [
            "No telemetry or KB retrieval results; cannot ground plan in evidence.",
            "Manual review required to confirm anomaly and next steps.",
        ]
    elif reason == "tool_failure":
        packet["what_we_dont_know"] = [
            "At least one required investigation tool failed; evidence may be incomplete.",
            "Automatic decision path is blocked by guardrails (fail-closed).",
        ]
        packet["what_to_check"].insert(
            0,
            "Inspect MCP/tool failure logs and retry only after tool health is restored.",
        )
    elif reason == "conflicting_signals":
        packet["what_to_check"].insert(
            0,
            "Resolve conflicting hypotheses (anomaly vs normal) with additional data.",
        )
    packet = _ensure_escalation_packet(
        incident_id, packet, trace_id=trace_id, audit_on_fallback=False
    )
    audit_append(
        trace_id=trace_id,
        incident_id=incident_id,
        actor="agent",
        tool="guardrail_escalation",
        args={"reason": reason},
        decision="escalate",
        outcome="success",
    )
    return {
        "escalated": True,
        "escalation_packet": packet,
        "output_schema_status": "ok",
        "output_schema_reason": "",
    }


def _normalize_plan_steps(
    plan: list,
    default_doc_ids: list[str] | None = None,
    default_snippet_ids: list[str] | None = None,
    *,
    fill_grounding: bool = False,
) -> None:
    """
    Ensure plan step dicts have action and action_type.

    PS4.1: ``fill_grounding`` must stay False before evidence policy checks. Auto-inserting
    citation IDs would bypass grounding validation (model must supply doc_ids/snippet_ids).
    """
    doc_ids = default_doc_ids or []
    snippet_ids = default_snippet_ids or []
    for step in plan:
        if isinstance(step, dict):
            step["action"] = step.get("action") or ""
            step["action_type"] = step.get("action_type") or "report"
            if (
                fill_grounding
                and not step.get("doc_ids")
                and not step.get("snippet_ids")
            ):
                step["doc_ids"] = doc_ids[:1] if doc_ids else []
                step["snippet_ids"] = snippet_ids[:1] if snippet_ids else []


def _evaluate_evidence_policy(state: AgentState) -> tuple[bool, str, str]:
    """
    PS4.1 evidence policy:
    - non-escalated outputs must have at least one citation identifier,
    - non-report plan steps must be grounded to citation identifiers.
    """
    citations = state.get("citations") or []
    plan = state.get("plan") or []
    if not isinstance(citations, list):
        citations = []
    if not isinstance(plan, list):
        plan = []

    citation_ids: set[str] = set()
    for c in citations:
        if not isinstance(c, dict):
            continue
        doc_id = str(c.get("doc_id") or "").strip()
        snippet_id = str(c.get("snippet_id") or "").strip()
        if doc_id:
            citation_ids.add(doc_id)
        if snippet_id:
            citation_ids.add(snippet_id)

    if not citation_ids:
        return (
            False,
            "evidence_policy_violation",
            "No valid citation identifiers available for grounding.",
        )

    for idx, step in enumerate(plan):
        if not isinstance(step, dict):
            continue
        action_type = str(step.get("action_type") or "report").strip().lower()
        if action_type == "report":
            continue
        refs: set[str] = set()
        for d in step.get("doc_ids") or []:
            s = str(d or "").strip()
            if s:
                refs.add(s)
        for sref in step.get("snippet_ids") or []:
            s = str(sref or "").strip()
            if s:
                refs.add(s)
        if not refs:
            return (
                False,
                "evidence_policy_violation",
                f"Plan step {idx} has no grounding references.",
            )
        if refs.isdisjoint(citation_ids):
            return (
                False,
                "evidence_policy_violation",
                f"Plan step {idx} references unsupported citations.",
            )
    return True, "ok", ""


def decide(state: AgentState) -> dict:
    """Produce plan; each step must reference at least one doc_id or snippet_id (NF5a). S1.12: token budget, rate limit, timeout."""
    incident_id = state.get("incident_id") or "unknown"
    trace_id = state.get("trace_id") or incident_id
    run_id = state.get("run_id") or trace_id
    tokens_used = state.get("tokens_used") or 0
    llm_calls_used = state.get("llm_calls_used") or 0
    token_budget = max(0, getattr(settings, "agent_token_budget_per_run", 0))
    max_llm_calls = max(0, getattr(settings, "agent_max_llm_calls_per_run", 0))
    if token_budget and tokens_used >= token_budget:
        return _escalation_for_limit_or_timeout(
            incident_id,
            "token_limit",
            f"Token budget ({token_budget}) already reached before decide.",
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    if max_llm_calls and llm_calls_used >= max_llm_calls:
        return _escalation_for_limit_or_timeout(
            incident_id,
            "rate_limit",
            f"Max LLM calls per run ({max_llm_calls}) already reached before decide.",
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    hypotheses = state.get("hypotheses") or []
    citations = state.get("citations") or []
    subsystem = state.get("subsystem") or "Ground"
    risk = state.get("risk") or "medium"
    doc_ids = list({c.get("doc_id") for c in citations if c.get("doc_id")})
    snippet_ids = list({c.get("snippet_id") for c in citations if c.get("snippet_id")})
    # S3.0: attach to same logical run_id for LLM observability.
    run_id = start_llm_run(
        run_id,
        incident_id=incident_id,
        node="decide",
    )
    decide_prompt = get_prompt(DECIDE_PROMPT_ID)
    investigation_notes, note_codes = sanitize_investigation_notes(hypotheses[:5])
    injection_codes = merge_detection_codes(
        list(state.get("injection_detection_codes") or []), note_codes
    )
    if note_codes:
        _audit_prompt_injection(
            trace_id=trace_id,
            incident_id=incident_id,
            source="decide_notes",
            codes=note_codes,
        )
    prompt = decide_prompt.text.format(
        subsystem=subsystem,
        risk=risk,
        investigation_notes=investigation_notes,
        doc_ids=doc_ids,
        snippet_ids=snippet_ids[:10],
    )
    tracer = get_tracer("apps.agent")
    with tracer.start_as_current_span("agent.decide", kind=SpanKind.INTERNAL) as sp:
        sp.set_attribute("incident_id", incident_id)
        sp.set_attribute("run_id", run_id)
        sp.set_attribute("tool", "llm_decide")
        try:
            from apps.model_selection import get_current_model_id

            model_id = get_current_model_id()
            gateway_result = gateway_generate(
                prompt=prompt,
                node="decide",
                model_id=model_id,
                temperature=0,
            )
            content = str(gateway_result.get("content") or "")
            usage_meta = gateway_result.get("usage") or {}
            usage = int(usage_meta.get("total_tokens") or 0)
        except LLMGatewayTimeoutError:
            sp.set_status(Status(StatusCode.ERROR, "llm timeout"))
            return _escalation_for_limit_or_timeout(
                incident_id, "llm_timeout", "LLM call timed out during decide."
            ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
        except LLMGatewayProviderError as exc:
            sp.set_status(Status(StatusCode.ERROR, "llm provider error"))
            return _escalation_for_limit_or_timeout(
                incident_id,
                "llm_provider_error",
                f"LLM provider error during decide: {exc}",
            ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    tokens_used += usage
    llm_calls_used += 1
    if token_budget and tokens_used > token_budget:
        return _escalation_for_limit_or_timeout(
            incident_id,
            "token_limit",
            f"Token budget ({token_budget}) exceeded during decide (used {tokens_used}).",
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    # S3.0: record LLM call in observability spine.
    log_llm_call(
        run_id,
        node="decide",
        model_id=model_id,
        prompt_id=decide_prompt.id,
        prompt_version=decide_prompt.version,
        tags={
            "subsystem": subsystem,
            "risk": risk,
        },
        metrics={
            "tokens_used": usage,
            "prompt_tokens": int(usage_meta.get("prompt_tokens") or 0),
            "completion_tokens": int(usage_meta.get("completion_tokens") or 0),
            "latency_ms": int(gateway_result.get("latency_ms") or 0),
        },
    )
    text = content.strip()
    if "```" in text:
        text = text.split("```")[1].replace("json", "").strip()
    try:
        plan = json.loads(text)
    except json.JSONDecodeError:
        plan = [
            {
                "action": "Escalate to ops",
                "safe": True,
                "doc_ids": doc_ids[:1] or [],
                "snippet_ids": snippet_ids[:1] or [],
            }
        ]
    if not isinstance(plan, list):
        plan = [plan]
    _normalize_plan_steps(plan, doc_ids, snippet_ids, fill_grounding=False)
    plan_ok, plan_reasons = validate_plan_allowlist(plan)
    if not plan_ok:
        plan_codes = merge_detection_codes(
            injection_codes,
            [f"plan_allowlist:{r[:80]}" for r in plan_reasons],
        )
        _audit_prompt_injection(
            trace_id=trace_id,
            incident_id=incident_id,
            source="decide_plan",
            codes=plan_codes,
        )
        return _escalation_for_prompt_injection(
            incident_id,
            detail=format_detection_detail(plan_codes, extra="plan failed allowlist"),
            codes=plan_codes,
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    return {
        "plan": plan,
        "tokens_used": tokens_used,
        "llm_calls_used": llm_calls_used,
        "injection_detection_codes": injection_codes,
        "injection_guard_status": "ok",
        "injection_guard_reason": "",
    }


def act(state: AgentState) -> dict:
    """
    S2.3: Execute safe steps via Ticketing/GitOps MCP; for restricted, call OPA
    and if allow create approval request; on deny/error escalate.
    """
    incident_id = state.get("incident_id") or "unknown"
    trace_id = state.get("trace_id") or incident_id
    plan = list(state.get("plan") or [])
    _normalize_plan_steps(plan, fill_grounding=False)
    if not state.get("escalated"):
        ok, reason, detail = _evaluate_evidence_policy(state)
        if not ok:
            packet = {
                "reason": reason,
                "what_we_know": [
                    f"Incident {incident_id}",
                    "Evidence policy rejected plan before Act execution.",
                    detail,
                ],
                "what_we_dont_know": [
                    "Proposed actions cannot be trusted without valid grounding.",
                ],
                "what_to_check": [
                    "Inspect investigation citations and plan references.",
                    "Ensure decide output includes doc_ids/snippet_ids per step.",
                ],
            }
            packet = _ensure_escalation_packet(
                incident_id, packet, trace_id=trace_id, audit_on_fallback=False
            )
            return {
                "escalated": True,
                "escalation_packet": packet,
                "evidence_policy_status": "violation",
                "evidence_policy_reason": reason,
                "act_results": [],
                "approval_requests": [],
            }
    plan_ok, plan_reasons = validate_plan_allowlist(plan)
    if not plan_ok:
        plan_codes = merge_detection_codes(
            list(state.get("injection_detection_codes") or []),
            [f"plan_allowlist:{r[:80]}" for r in plan_reasons],
        )
        _audit_prompt_injection(
            trace_id=trace_id,
            incident_id=incident_id,
            source="act_plan",
            codes=plan_codes,
        )
        return _escalation_for_prompt_injection(
            incident_id,
            detail=format_detection_detail(plan_codes, extra="act blocked plan"),
            codes=plan_codes,
        )
    act_results: list[dict] = []
    approval_requests: list[dict] = []
    tracer = get_tracer("apps.agent")
    run_id = state.get("run_id") or trace_id

    for i, step in enumerate(plan):
        if not isinstance(step, dict):
            continue
        safe = step.get("safe", True)
        action_type = (step.get("action_type") or "report").strip().lower()
        action_text = step.get("action", "") or ""

        if safe and action_type == "create_ticket":
            with tracer.start_as_current_span("mcp.create_ticket") as sp:
                sp.set_attribute("incident_id", incident_id)
                sp.set_attribute("run_id", run_id)
                sp.set_attribute("tool", "create_ticket")
                try:
                    ticket = call_create_ticket(
                        title=action_text[:200], body=action_text
                    )
                    outcome = "success" if ticket else "empty"
                    err_msg = None
                except Exception as exc:
                    ticket = None
                    outcome = "failure"
                    err_msg = _safe_error_message(exc)
                    sp.set_status(Status(StatusCode.ERROR, err_msg))
            audit_append(
                trace_id=trace_id,
                incident_id=incident_id,
                actor="agent",
                tool="create_ticket",
                args={"title": action_text[:100], "body_len": len(action_text)},
                outcome=outcome,
                error_message=err_msg,
            )
            act_results.append(
                {
                    "step_index": i,
                    "tool": "create_ticket",
                    "outcome": outcome,
                    "result": ticket,
                }
            )

        elif safe and action_type == "create_pr":
            branch = f"agent/{incident_id}"
            files = [
                {
                    "path": "alerts/agent-proposed.yaml",
                    "content": f"# Agent proposal: {action_text}\n",
                }
            ]
            with tracer.start_as_current_span("mcp.create_pr") as sp:
                sp.set_attribute("incident_id", incident_id)
                sp.set_attribute("run_id", run_id)
                sp.set_attribute("tool", "create_pr")
                try:
                    pr_result = call_create_pr(
                        repo_path=None, branch=branch, files=files
                    )
                    outcome = "success" if pr_result else "empty"
                    err_msg = None
                except Exception as exc:
                    pr_result = None
                    outcome = "failure"
                    err_msg = _safe_error_message(exc)
                    sp.set_status(Status(StatusCode.ERROR, err_msg))
            audit_append(
                trace_id=trace_id,
                incident_id=incident_id,
                actor="agent",
                tool="create_pr",
                args={"branch": branch, "files_count": len(files)},
                outcome=outcome,
                error_message=err_msg,
            )
            act_results.append(
                {
                    "step_index": i,
                    "tool": "create_pr",
                    "outcome": outcome,
                    "result": pr_result,
                }
            )

        elif not safe:
            with tracer.start_as_current_span("policy.opa_check") as sp:
                sp.set_attribute("incident_id", incident_id)
                sp.set_attribute("run_id", run_id)
                sp.set_attribute("tool", "opa_allow")
                allowed = opa_allow(step, incident_id)
                if not allowed:
                    sp.set_status(Status(StatusCode.ERROR, "opa deny/unavailable"))
            if allowed:
                request_id = approval_store_create(
                    incident_id=incident_id,
                    step_index=i,
                    step=step,
                    reason="restricted",
                )
                approval_requests.append(
                    {
                        "id": request_id,
                        "step_index": i,
                        "step": step,
                        "incident_id": incident_id,
                        "reason": "restricted",
                    }
                )
                audit_append(
                    trace_id=trace_id,
                    incident_id=incident_id,
                    actor="agent",
                    tool="approval_request",
                    args={"step_index": i, "action": action_text[:80]},
                    outcome="success",
                )
            else:
                packet: EscalationPacket = {
                    "reason": "policy_deny",
                    "what_we_know": [
                        f"Incident {incident_id}",
                        f"Restricted step denied by policy: {action_text[:100]}",
                    ],
                    "what_we_dont_know": [
                        "OPA denied or unavailable; step not executed."
                    ],
                    "what_to_check": [
                        "Review OPA policy (S2.4) and approval flow.",
                        "If step is valid, create approval request via API (S2.5).",
                    ],
                }
                audit_append(
                    trace_id=trace_id,
                    incident_id=incident_id,
                    actor="agent",
                    tool="opa_check",
                    args={"step_index": i},
                    outcome="failure",
                    error_message="OPA deny or unavailable",
                )
                packet = _ensure_escalation_packet(
                    incident_id, packet, trace_id=trace_id, audit_on_fallback=True
                )
                try:
                    safe_results = validate_act_results(act_results)
                except OutputSchemaViolation:
                    safe_results = []
                return {
                    "act_results": safe_results,
                    "approval_requests": approval_requests,
                    "escalated": True,
                    "escalation_packet": packet,
                    "output_schema_status": "ok"
                    if packet.get("reason") != OUTPUT_SCHEMA_VIOLATION
                    else "violation",
                    "output_schema_reason": ""
                    if packet.get("reason") != OUTPUT_SCHEMA_VIOLATION
                    else OUTPUT_SCHEMA_VIOLATION,
                }

    try:
        safe_results = validate_act_results(act_results)
        safe_approvals = validate_approval_requests(approval_requests)
    except OutputSchemaViolation as exc:
        packet = escalation_packet_for_schema_violation(
            incident_id,
            envelope=exc.envelope,
            detail=exc.operator_message,
        )
        _audit_schema_guardrail(
            trace_id=trace_id,
            incident_id=incident_id,
            envelope=exc.envelope,
            detail=exc.operator_message,
        )
        return {
            "act_results": [],
            "approval_requests": [],
            "escalated": True,
            "escalation_packet": packet,
            "output_schema_status": "violation",
            "output_schema_reason": OUTPUT_SCHEMA_VIOLATION,
        }
    return {
        "act_results": safe_results,
        "approval_requests": safe_approvals,
    }


def report(state: AgentState) -> dict:
    """Format summary, evidence, actions, rollback, trace link. Include escalation packet when escalated (F10)."""
    incident_id = state.get("incident_id") or "unknown"
    subsystem = state.get("subsystem") or ""
    risk = state.get("risk") or ""
    hypotheses = state.get("hypotheses") or []
    citations = state.get("citations") or []
    plan = state.get("plan") or []
    escalated = state.get("escalated") or False
    escalation_packet = state.get("escalation_packet") or {}
    evidence_policy_status = "n/a"
    evidence_policy_reason = ""
    injection_guard_status = state.get("injection_guard_status") or "ok"
    injection_guard_reason = state.get("injection_guard_reason") or ""
    if escalated:
        injection_guard_status = (
            state.get("injection_guard_status") or "skipped_escalated"
        )
    plan_for_policy = list(state.get("plan") or [])
    _normalize_plan_steps(plan_for_policy, fill_grounding=False)
    if not escalated:
        policy_state: AgentState = {**state, "plan": plan_for_policy}
        ok, reason, detail = _evaluate_evidence_policy(policy_state)
        if not ok:
            evidence_policy_status = "violation"
            evidence_policy_reason = reason
            escalated = True
            escalation_packet = {
                "reason": reason,
                "what_we_know": [
                    f"Incident {incident_id}",
                    "Evidence policy guard rejected non-grounded output.",
                    detail,
                ],
                "what_we_dont_know": [
                    "Proposed actions cannot be trusted without valid grounding.",
                ],
                "what_to_check": [
                    "Inspect investigation citations and plan references.",
                    "Re-run after MCP evidence sources are healthy.",
                ],
            }
        else:
            evidence_policy_status = "ok"
    else:
        evidence_policy_status = "skipped_escalated"
    # S1.10: trace_id from OTel (32-char hex) when exporting; else incident_id
    trace_id_raw = state.get("trace_id") or ""
    trace_url = (
        f"{settings.jaeger_ui_url}/trace/{trace_id_raw}"
        if is_valid_trace_id_hex(trace_id_raw)
        else ""
    )
    trace_id = trace_id_raw or incident_id
    cite_refs = list(
        {
            c.get("doc_id") or c.get("snippet_id")
            for c in citations
            if c.get("doc_id") or c.get("snippet_id")
        }
    )
    act_results = state.get("act_results") or []
    approval_requests = state.get("approval_requests") or []
    output_schema_status = "ok"
    output_schema_reason = ""

    def _assemble_report(
        *,
        esc: bool,
        packet: dict,
        results: list[dict],
        approvals: list[dict],
    ) -> dict:
        obj: dict = {
            "schema_version": "v1",
            "incident_id": incident_id,
            "run_id": str(state.get("run_id") or trace_id or incident_id),
            "executive_summary": (
                f"[ESCALATION] Incident {incident_id}: handoff to human. Reason: {packet.get('reason', 'unknown')}."
                if esc
                else f"Incident {incident_id}: subsystem={subsystem}, risk={risk}. {len(hypotheses)} investigation notes."
            ),
            "evidence": [{"hypothesis": h} for h in hypotheses[:5]],
            "citation_refs": cite_refs,
            "proposed_actions": [
                p.get("action", "") for p in plan if isinstance(p, dict)
            ],
            "rollback": "Revert config changes via ops-config PR; no automated rollback in MVP.",
            "trace_link": trace_url,
        }
        if results:
            obj["act_results"] = results
        if approvals:
            obj["approval_requests"] = approvals
        if esc:
            obj["escalation_packet"] = packet
            obj["handoff"] = (
                "Agent could not proceed with confidence; manual review required. See escalation_packet."
            )
        return obj

    try:
        safe_results = validate_act_results(act_results) if act_results else []
        safe_approvals = (
            validate_approval_requests(approval_requests) if approval_requests else []
        )
        if escalated:
            escalation_packet = validate_escalation_packet(escalation_packet)
        report_obj = _assemble_report(
            esc=escalated,
            packet=escalation_packet,
            results=safe_results,
            approvals=safe_approvals,
        )
        validate_run_report(report_obj)
    except OutputSchemaViolation as exc:
        output_schema_status = "violation"
        output_schema_reason = OUTPUT_SCHEMA_VIOLATION
        escalated = True
        _audit_schema_guardrail(
            trace_id=trace_id,
            incident_id=incident_id,
            envelope=exc.envelope,
            detail=exc.operator_message,
        )
        escalation_packet = escalation_packet_for_schema_violation(
            incident_id,
            envelope=exc.envelope,
            detail=exc.operator_message,
        )
        report_obj = _assemble_report(
            esc=True,
            packet=escalation_packet,
            results=[],
            approvals=[],
        )
        validate_run_report(report_obj)

    return {
        "report": report_obj,
        "escalated": bool(escalated),
        "escalation_packet": escalation_packet if escalated else {},
        "evidence_policy_status": evidence_policy_status,
        "evidence_policy_reason": evidence_policy_reason,
        "output_schema_status": output_schema_status,
        "output_schema_reason": output_schema_reason,
        "injection_guard_status": injection_guard_status,
        "injection_guard_reason": injection_guard_reason,
    }
