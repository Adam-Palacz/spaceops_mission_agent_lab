"""
S2.3/S2.4 — OPA client stub for restricted-action policy.
When S2.4 is implemented, this will call OPA; until then, fail-closed (deny).
"""

from __future__ import annotations


def opa_allow(step: dict, incident_id: str) -> bool:
    """
    Check whether OPA allows the given restricted step.
    S2.4: real implementation will call OPA; until then, deny (fail-closed).
    """
    _ = step, incident_id
    return False
