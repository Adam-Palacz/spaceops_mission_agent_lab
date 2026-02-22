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
from apps.agent.state import AgentState, Citation, PlanStep
from apps.agent.mcp_client import (
    call_telemetry,
    call_search_runbooks,
    call_search_postmortems,
    signature_from_payload,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_INCIDENTS = REPO_ROOT / "data" / "incidents"

_SUBSYSTEMS = ("ADCS", "Power", "Thermal", "Comms", "Payload", "Ground")

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


def _chat_completion(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0) -> str:
    """Call OpenAI Chat Completions API; return assistant message content."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY required for agent; set in .env")
    with httpx.Client(timeout=60.0) as client:
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
    return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""


def triage(state: AgentState) -> dict:
    """Classify subsystem and risk; persist incident record."""
    incident_id = state.get("incident_id") or "unknown"
    payload = state.get("payload") or {}
    prompt = f"""Classify this incident. Payload: {payload}
Return exactly two words on one line, separated by a space: SUBSYSTEM RISK
SUBSYSTEM must be one of: {', '.join(_SUBSYSTEMS)}
RISK must be one of: low, medium, high
Example: Power medium"""
    content = _chat_completion(prompt)
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
    return {"subsystem": subsystem, "risk": risk}


def investigate(state: AgentState) -> dict:
    """Call Telemetry and KB MCPs; attach hypotheses and citations."""
    payload = state.get("payload") or {}
    subsystem = state.get("subsystem") or "Ground"
    query = signature_from_payload(payload) or subsystem.lower()
    # Time range from payload or default window
    start = (payload.get("time_range_start") or "2025-02-14T09:00:00Z")
    end = (payload.get("time_range_end") or "2025-02-14T11:00:00Z")
    channels = payload.get("channels")
    telemetry = call_telemetry(start, end, channels if isinstance(channels, list) else None)
    runbooks = call_search_runbooks(query, 5)
    postmortems = call_search_postmortems(query, 5)
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


def decide(state: AgentState) -> dict:
    """Produce plan; each step must reference at least one doc_id or snippet_id (NF5a)."""
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
    content = _chat_completion(prompt)
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
    return {"plan": plan}


def report(state: AgentState) -> dict:
    """Format summary, evidence, actions, rollback, trace link."""
    incident_id = state.get("incident_id") or "unknown"
    subsystem = state.get("subsystem") or ""
    risk = state.get("risk") or ""
    hypotheses = state.get("hypotheses") or []
    citations = state.get("citations") or []
    plan = state.get("plan") or []
    trace_url = f"{settings.jaeger_ui_url}/trace/{incident_id}"  # placeholder; real trace in S1.10
    cite_refs = list({c.get("doc_id") or c.get("snippet_id") for c in citations if c.get("doc_id") or c.get("snippet_id")})
    report_obj = {
        "incident_id": incident_id,
        "executive_summary": f"Incident {incident_id}: subsystem={subsystem}, risk={risk}. {len(hypotheses)} investigation notes.",
        "evidence": [{"hypothesis": h} for h in hypotheses[:5]],
        "citation_refs": cite_refs,
        "proposed_actions": [p.get("action", "") for p in plan if isinstance(p, dict)],
        "rollback": "Revert config changes via ops-config PR; no automated rollback in MVP.",
        "trace_link": trace_url,
    }
    return {"report": report_obj}
