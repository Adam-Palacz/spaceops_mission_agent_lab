"""
Prompt registry (S3.2) — centralised, versioned prompts for agent nodes.

Prompts are referenced by stable IDs; metadata includes version and description.
Nodes (triage, decide, etc.) load prompts via this registry instead of hard-coded
string literals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Prompt:
    id: str
    version: str
    description: str
    text: str


_PROMPTS: Dict[str, Prompt] = {
    "triage": Prompt(
        id="triage",
        version="v1",
        description="Classify incident into subsystem and risk level.",
        text=(
            "Classify this incident.\n"
            "Payload: {payload}\n"
            "Return exactly two words on one line, separated by a space: SUBSYSTEM RISK\n"
            "SUBSYSTEM must be one of: {subsystems}\n"
            "RISK must be one of: low, medium, high\n"
            "Example: Power medium"
        ),
    ),
    "decide": Prompt(
        id="decide",
        version="v1",
        description="Produce a short, citation-grounded action plan.",
        text=(
            "Given subsystem={subsystem}, risk={risk}, and investigation:\n"
            "{investigation_notes}\n\n"
            "Produce a short action plan. Each step MUST cite at least one of these doc_ids or snippet_ids:\n"
            "doc_ids: {doc_ids}\n"
            "snippet_ids: {snippet_ids}\n\n"
            "Return a JSON array of steps. Each step: "
            '{{"action": "...", "safe": true|false, '
            '"action_type": "create_ticket"|"create_pr"|"change_config"|"report", '
            '"doc_ids": ["..."], "snippet_ids": ["..."]}}\n'
            "- safe=true for ticket, report, extra query; safe=false for config change/restart (restricted).\n"
            '- action_type: use "create_ticket" for creating a ticket, "create_pr" for proposing a config/PR '
            'change, "change_config" for restricted config changes, "report" for documentation-only.\n'
            "Output only the JSON array, no markdown."
        ),
    ),
}


def get_prompt(prompt_id: str) -> Prompt:
    """
    Return the Prompt object for the given id.

    Raises KeyError if the id is unknown.
    """
    return _PROMPTS[prompt_id]


TRIAGE_PROMPT_ID = "triage"
DECIDE_PROMPT_ID = "decide"
