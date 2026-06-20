"""PS7.7 — Deterministic multi-cloud burst routing policy (simulation; no live cloud B)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BurstRoutingSignals:
    """Inputs for rule-based burst routing (cloud A primary, cloud B burst)."""

    kill_switch: bool
    burst_enabled: bool
    primary_backend: str
    burst_backend: str
    primary_healthy: bool
    burst_healthy: bool
    budget_ok: bool
    burst_within_cost_ceiling: bool
    burst_latency_p95_ms: int | None
    latency_sla_ms: int


@dataclass(frozen=True)
class BurstRoutingDecision:
    backend_to_use: str
    backend_routing_reason: str
    used_burst: bool
    fallback_to_primary: bool


def decide_burst_route(signals: BurstRoutingSignals) -> BurstRoutingDecision:
    """Return deterministic backend choice and audit reason for the same signals."""
    primary = signals.primary_backend.strip() or "openai"
    burst = signals.burst_backend.strip() or "gpu"

    if signals.kill_switch:
        return BurstRoutingDecision(
            backend_to_use=primary,
            backend_routing_reason="kill_switch_active",
            used_burst=False,
            fallback_to_primary=True,
        )

    if not signals.burst_enabled:
        return BurstRoutingDecision(
            backend_to_use=primary,
            backend_routing_reason="burst_disabled",
            used_burst=False,
            fallback_to_primary=True,
        )

    if not signals.budget_ok:
        return BurstRoutingDecision(
            backend_to_use=primary,
            backend_routing_reason="budget_exceeded",
            used_burst=False,
            fallback_to_primary=True,
        )

    if not signals.burst_healthy:
        return BurstRoutingDecision(
            backend_to_use=primary,
            backend_routing_reason="burst_unavailable",
            used_burst=False,
            fallback_to_primary=True,
        )

    if not signals.burst_within_cost_ceiling:
        return BurstRoutingDecision(
            backend_to_use=primary,
            backend_routing_reason="burst_cost_ceiling",
            used_burst=False,
            fallback_to_primary=True,
        )

    if (
        signals.burst_latency_p95_ms is not None
        and signals.latency_sla_ms > 0
        and signals.burst_latency_p95_ms > signals.latency_sla_ms
    ):
        return BurstRoutingDecision(
            backend_to_use=primary,
            backend_routing_reason="burst_latency_sla",
            used_burst=False,
            fallback_to_primary=True,
        )

    if not signals.primary_healthy and signals.burst_healthy:
        return BurstRoutingDecision(
            backend_to_use=burst,
            backend_routing_reason="primary_unhealthy_burst_takeover",
            used_burst=True,
            fallback_to_primary=False,
        )

    return BurstRoutingDecision(
        backend_to_use=burst,
        backend_routing_reason="burst_policy_match",
        used_burst=True,
        fallback_to_primary=False,
    )


def explain_gateway_routing_reason(
    *,
    backend_requested: str,
    backend_actual: str,
    fallback_used: bool,
    fallback_reason: str,
    kill_switch: bool = False,
    burst_policy_reason: str | None = None,
) -> str:
    """Audit string for a real gateway call (PS7.7)."""
    if kill_switch:
        return "kill_switch_active"
    if fallback_used and fallback_reason:
        return f"fallback:{fallback_reason}"
    base = f"configured:{backend_actual or backend_requested}"
    if burst_policy_reason and burst_policy_reason not in base:
        return f"{base};policy:{burst_policy_reason}"
    return base
