"""
SpaceOps Agent — pipeline nodes: Triage, Investigate, Decide, Report (S1.7).
Uses OpenAI Chat Completions API via httpx (avoids LangChain/Pydantic BaseCache issue).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from config import settings
from apps.agent.state import AgentState, Citation, EscalationPacket
from apps.agent.mcp_client import (
    call_telemetry,
    call_search_runbooks,
    call_search_postmortems,
    signature_from_payload,
)
from apps.agent.audit_log import append_entry as audit_append
from apps.telemetry import get_tracer

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_INCIDENTS = REPO_ROOT / "data" / "incidents"

_SUBSYSTEMS = ("ADCS", "Power", "Thermal", "Comms", "Payload", "Ground")

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


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


def _chat_completion(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0) -> tuple[str, int]:
    """
    Call OpenAI Chat Completions API. Return (content, total_tokens).
    S1.12: uses agent_llm_call_timeout_seconds; raises httpx.TimeoutException on timeout.
    """
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY required for agent; set in .env")
    timeout = max(1, getattr(settings, "agent_llm_call_timeout_seconds", 30))
    with httpx.Client(timeout=float(timeout)) as client:
        r = client.post(
            OPENAI_CHAT_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        r.raise_for_status()
        data = r.json()
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    usage = (data.get("usage") or {}).get("total_tokens") or 0
    return content, usage


def triage(state: AgentState) -> dict:
    """Classify subsystem and risk; persist incident record. S1.12: token budget, rate limit, LLM timeout → escalate."""
    incident_id = state.get("incident_id") or "unknown"
    payload = state.get("payload") or {}
    tokens_used = state.get("tokens_used") or 0
    llm_calls_used = state.get("llm_calls_used") or 0
    token_budget = max(0, getattr(settings, "agent_token_budget_per_run", 0))
    max_llm_calls = max(0, getattr(settings, "agent_max_llm_calls_per_run", 0))
    if token_budget and tokens_used >= token_budget:
        return _escalation_for_limit_or_timeout(
            incident_id, "token_limit", f"Token budget ({token_budget}) already reached before triage."
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    if max_llm_calls and llm_calls_used >= max_llm_calls:
        return _escalation_for_limit_or_timeout(
            incident_id, "rate_limit", f"Max LLM calls per run ({max_llm_calls}) already reached before triage."
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    prompt = f"""Classify this incident. Payload: {payload}
Return exactly two words on one line, separated by a space: SUBSYSTEM RISK
SUBSYSTEM must be one of: {', '.join(_SUBSYSTEMS)}
RISK must be one of: low, medium, high
Example: Power medium"""
    try:
        content, usage = _chat_completion(prompt)
    except httpx.TimeoutException:
        return _escalation_for_limit_or_timeout(
            incident_id, "llm_timeout", "LLM call timed out during triage."
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    tokens_used += usage
    llm_calls_used += 1
    if token_budget and tokens_used > token_budget:
        return _escalation_for_limit_or_timeout(
            incident_id, "token_limit", f"Token budget ({token_budget}) exceeded during triage (used {tokens_used})."
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
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
    return {"subsystem": subsystem, "risk": risk, "tokens_used": tokens_used, "llm_calls_used": llm_calls_used}


def investigate(state: AgentState) -> dict:
    """Call Telemetry and KB MCPs; attach hypotheses and citations. S1.9: audit each tool call."""
    payload = state.get("payload") or {}
    subsystem = state.get("subsystem") or "Ground"
    query = signature_from_payload(payload) or subsystem.lower()
    incident_id = state.get("incident_id") or "unknown"
    trace_id = state.get("trace_id") or incident_id
    # Time range from payload or default window
    start = (payload.get("time_range_start") or "2025-02-14T09:00:00Z")
    end = (payload.get("time_range_end") or "2025-02-14T11:00:00Z")
    channels = payload.get("channels")
    # Tool call + audit (S1.9) + span per tool (S1.10)
    tracer = get_tracer("apps.agent")
    telemetry_args = {"time_range_start": start, "time_range_end": end, "channels": channels if isinstance(channels, list) else []}
    with tracer.start_as_current_span("mcp.query_telemetry") as sp:
        sp.set_attribute("incident_id", incident_id)
        telemetry = call_telemetry(start, end, channels if isinstance(channels, list) else None)
    audit_append(trace_id=trace_id, incident_id=incident_id, actor="agent", tool="query_telemetry", args=telemetry_args, outcome="success")
    runbooks_args = {"query": query, "limit": 5}
    with tracer.start_as_current_span("mcp.search_runbooks") as sp:
        sp.set_attribute("incident_id", incident_id)
        runbooks = call_search_runbooks(query, 5)
    audit_append(trace_id=trace_id, incident_id=incident_id, actor="agent", tool="search_runbooks", args=runbooks_args, outcome="success")
    postmortems_args = {"signature": query, "limit": 5}
    with tracer.start_as_current_span("mcp.search_postmortems") as sp:
        sp.set_attribute("incident_id", incident_id)
        postmortems = call_search_postmortems(query, 5)
    audit_append(trace_id=trace_id, incident_id=incident_id, actor="agent", tool="search_postmortems", args=postmortems_args, outcome="success")
    hypotheses: list[str] = []
    citations: list[Citation] = []
    if telemetry:
        hypotheses.append(f"Telemetry: {len(telemetry)} samples in range; review for anomalies.")
        for i, r in enumerate(telemetry[:5]):
            citations.append({"snippet_id": f"telemetry_{i}", "content": str(r), "doc_id": "telemetry"})
    for chunk in runbooks:
        if isinstance(chunk, dict) and chunk.get("doc_id"):
            hypotheses.append(f"Runbook: {chunk.get('content', '')[:200]}...")
            citations.append({
                "doc_id": chunk.get("doc_id", ""),
                "content": chunk.get("content", ""),
                "snippet_id": f"runbook_{chunk.get('doc_id', '')}",
            })
    for chunk in postmortems:
        if isinstance(chunk, dict) and chunk.get("doc_id"):
            hypotheses.append(f"Postmortem: {chunk.get('content', '')[:200]}...")
            citations.append({
                "doc_id": chunk.get("doc_id", ""),
                "content": chunk.get("content", ""),
                "snippet_id": f"postmortem_{chunk.get('doc_id', '')}",
            })
    if not hypotheses:
        hypotheses.append("No telemetry or KB hits; escalate for manual review.")
    return {"hypotheses": hypotheses, "citations": citations}


def _should_escalate(state: AgentState) -> tuple[bool, str]:
    """Return (escalate, reason). Conditions: no evidence, high risk + no citations, conflicting signals (F10)."""
    hypotheses = state.get("hypotheses") or []
    citations = state.get("citations") or []
    risk = (state.get("risk") or "").lower()
    # No evidence: only the fallback "No telemetry or KB hits" or no citations
    no_evidence = not citations or (
        len(hypotheses) == 1 and "No telemetry or KB hits" in (hypotheses[0] or "")
    )
    if no_evidence:
        return True, "no_evidence"
    # High risk with no supporting citations
    if risk == "high" and len(citations) == 0:
        return True, "high_risk_no_evidence"
    # Conflicting signals: both "anomaly" and "normal" or "within limits" in hypotheses (simple heuristic)
    text = " ".join(hypotheses).lower()
    if "anomaly" in text and ("normal" in text or "within limits" in text):
        return True, "conflicting_signals"
    return False, ""


def check_escalation(state: AgentState) -> dict:
    """S1.8: Evaluate escalation conditions; if met, set escalation_packet (F10). S1.12: preserve limit/timeout escalation."""
    # Preserve escalation already set by token_limit, llm_timeout, or run_timeout (NF6)
    if state.get("escalated") and state.get("escalation_packet", {}).get("reason") in (
        "token_limit", "rate_limit", "llm_timeout", "run_timeout"
    ):
        return {"escalated": True, "escalation_packet": state.get("escalation_packet") or {}}
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
    elif reason == "conflicting_signals":
        packet["what_to_check"].insert(0, "Resolve conflicting hypotheses (anomaly vs normal) with additional data.")
    return {"escalated": True, "escalation_packet": packet}


def decide(state: AgentState) -> dict:
    """Produce plan; each step must reference at least one doc_id or snippet_id (NF5a). S1.12: token budget, rate limit, timeout."""
    incident_id = state.get("incident_id") or "unknown"
    tokens_used = state.get("tokens_used") or 0
    llm_calls_used = state.get("llm_calls_used") or 0
    token_budget = max(0, getattr(settings, "agent_token_budget_per_run", 0))
    max_llm_calls = max(0, getattr(settings, "agent_max_llm_calls_per_run", 0))
    if token_budget and tokens_used >= token_budget:
        return _escalation_for_limit_or_timeout(
            incident_id, "token_limit", f"Token budget ({token_budget}) already reached before decide."
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    if max_llm_calls and llm_calls_used >= max_llm_calls:
        return _escalation_for_limit_or_timeout(
            incident_id, "rate_limit", f"Max LLM calls per run ({max_llm_calls}) already reached before decide."
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    hypotheses = state.get("hypotheses") or []
    citations = state.get("citations") or []
    subsystem = state.get("subsystem") or "Ground"
    risk = state.get("risk") or "medium"
    doc_ids = list({c.get("doc_id") for c in citations if c.get("doc_id")})
    snippet_ids = list({c.get("snippet_id") for c in citations if c.get("snippet_id")})
    prompt = f"""Given subsystem={subsystem}, risk={risk}, and investigation:
{chr(10).join(hypotheses[:5])}

Produce a short action plan. Each step MUST cite at least one of these doc_ids or snippet_ids:
doc_ids: {doc_ids}
snippet_ids: {snippet_ids[:10]}

Return a JSON array of steps. Each step: {{"action": "...", "safe": true|false, "doc_ids": ["..."], "snippet_ids": ["..."]}}
Safe=true for ticket/report/query; safe=false for config/restart (restricted).
Output only the JSON array, no markdown."""
    try:
        content, usage = _chat_completion(prompt)
    except httpx.TimeoutException:
        return _escalation_for_limit_or_timeout(
            incident_id, "llm_timeout", "LLM call timed out during decide."
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    tokens_used += usage
    llm_calls_used += 1
    if token_budget and tokens_used > token_budget:
        return _escalation_for_limit_or_timeout(
            incident_id, "token_limit", f"Token budget ({token_budget}) exceeded during decide (used {tokens_used})."
        ) | {"tokens_used": tokens_used, "llm_calls_used": llm_calls_used}
    text = content.strip()
    if "```" in text:
        text = text.split("```")[1].replace("json", "").strip()
    try:
        plan = json.loads(text)
    except json.JSONDecodeError:
        plan = [{"action": "Escalate to ops", "safe": True, "doc_ids": doc_ids[:1] or [], "snippet_ids": snippet_ids[:1] or []}]
    if not isinstance(plan, list):
        plan = [plan]
    # Ensure each step has at least one citation
    for step in plan:
        if isinstance(step, dict):
            if not step.get("doc_ids") and not step.get("snippet_ids"):
                step["doc_ids"] = doc_ids[:1] if doc_ids else []
                step["snippet_ids"] = snippet_ids[:1] if snippet_ids else []
    return {"plan": plan, "tokens_used": tokens_used, "llm_calls_used": llm_calls_used}


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
    # S1.10: trace_id from OTel (32-char hex) when exporting; else incident_id
    trace_id = state.get("trace_id") or incident_id
    trace_url = f"{settings.jaeger_ui_url}/trace/{trace_id}"
    cite_refs = list({c.get("doc_id") or c.get("snippet_id") for c in citations if c.get("doc_id") or c.get("snippet_id")})
    report_obj: dict = {
        "incident_id": incident_id,
        "executive_summary": (
            f"[ESCALATION] Incident {incident_id}: handoff to human. Reason: {escalation_packet.get('reason', 'unknown')}."
            if escalated
            else f"Incident {incident_id}: subsystem={subsystem}, risk={risk}. {len(hypotheses)} investigation notes."
        ),
        "evidence": [{"hypothesis": h} for h in hypotheses[:5]],
        "citation_refs": cite_refs,
        "proposed_actions": [p.get("action", "") for p in plan if isinstance(p, dict)],
        "rollback": "Revert config changes via ops-config PR; no automated rollback in MVP.",
        "trace_link": trace_url,
    }
    if escalated:
        report_obj["escalation_packet"] = escalation_packet
        report_obj["handoff"] = "Agent could not proceed with confidence; manual review required. See escalation_packet."
    return {"report": report_obj}
